"""FastAPI entrypoint for the separated frontend and backend dashboard."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from ...services.dashboard_service import DashboardService
from ...services.events_outlook_service import EventOutlookValidationError, EventsOutlookService
from ...services.macro_data_service import MacroDataService, MacroDataValidationError
from ...services.market_data_service import MarketDataService
from ...services.market_data_repository import MarketDataValidationError
from ...services.push_center_service import PushCenterService
from ...providers.contracts import ProviderAvailability, ProviderStatus
from .spa_assets import WORKBENCH_ROUTES, build_spa_unavailable_response, load_spa_assets

logger = logging.getLogger(__name__)


class _UnavailableEventOutlookResearchProvider:
    """Event Outlook 默认研究 provider，用于测试桩未暴露研究能力时的兜底。

    Args:
        无初始化参数。

    Returns:
        提供空采集结果和不可用健康状态的轻量 provider。
    """

    provider_key = "event-outlook-unavailable"

    def collect_outlook(self, **_: object) -> list[object]:
        """返回空事件研究结果，避免非 Event Outlook 测试被外部依赖影响。"""
        return []

    def healthcheck(self) -> ProviderStatus:
        """返回不可用状态，让旧版窗口快照走降级语义。"""
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.UNAVAILABLE,
            detail="event outlook research provider is not configured",
            checked_at="1970-01-01T00:00:00Z",
        )


def _resolve_event_outlook_research_provider(dashboard_service: object) -> object:
    """解析 Event Outlook 可用的研究 provider。

    Args:
        dashboard_service: 当前注入的 Dashboard 服务或测试替身。

    Returns:
        Dashboard 服务上的研究 provider；不存在时返回本地不可用兜底 provider。
    """
    return getattr(dashboard_service, "_research_provider", _UnavailableEventOutlookResearchProvider())


def render_error_html(title: str, message: str) -> bytes:
    """渲染通用错误页。

    Args:
        title: 错误标题。
        message: 面向用户展示的错误说明。

    Returns:
        可直接写入 HTMLResponse 的 UTF-8 HTML 字节串。
    """
    return (
        "<!doctype html>"
        "<html lang='en'>"
        "<head><meta charset='utf-8'><title>{title}</title></head>"
        "<body><main><h1>{title}</h1><p>{message}</p></main></body>"
        "</html>"
    ).format(title=title, message=message).encode("utf-8")


def create_fastapi_app(
    dashboard_service: DashboardService | None = None,
    push_center_service: PushCenterService | None = None,
    macro_data_service: MacroDataService | None = None,
    market_data_service: MarketDataService | None = None,
    event_outlook_service: EventsOutlookService | None = None,
) -> FastAPI:
    """创建开发 Web 服务使用的 FastAPI 应用。

    Args:
        dashboard_service: Dashboard 聚合服务。
        push_center_service: 推送中心服务。
        macro_data_service: Macro Data 模块服务。
        event_outlook_service: Event Outlook 时间轴服务。

    Returns:
        已注册前端工作台接口和 SPA 路由的 FastAPI 应用。
    """
    service = dashboard_service or DashboardService()
    push_service = push_center_service or PushCenterService(
        dashboard_service=service,
        enable_scheduler=True,
    )
    macro_service = macro_data_service or MacroDataService()
    market_service = market_data_service or MarketDataService()
    event_service = event_outlook_service or EventsOutlookService(
        research_provider=_resolve_event_outlook_research_provider(service)
    )
    app = FastAPI(
        title="Finance And Policy Intelligence Dashboard",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    spa_assets = load_spa_assets()
    spa_assets_dir = spa_assets.dist_dir / "assets"
    if spa_assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=spa_assets_dir), name="spa-assets")

    def _loading_response(payload: dict[str, object], detail: str) -> JSONResponse:
        module = payload.get("module")
        if isinstance(module, dict):
            module["loading"] = True
            module["note"] = detail
        payload["refresh_after_ms"] = 2000
        return JSONResponse(payload, status_code=202)

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.on_event("shutdown")
    def shutdown_background_refresh() -> None:
        service.stop_background_refresh()
        push_service.stop_scheduler()

    @app.get("/api/frontend/modules/push")
    def frontend_push_module(refresh: bool = False, include_preview: bool = True) -> JSONResponse:
        try:
            if not refresh:
                loading, detail = push_service.should_serve_loading_module()
                if loading:
                    return _loading_response(
                        push_service.build_module_payload(include_preview=include_preview),
                        detail,
                    )
            payload = push_service.build_module_payload(
                force_refresh_preview=refresh,
                include_preview=include_preview,
            )
            payload["refresh_after_ms"] = push_service.frontend_auto_refresh_ms
            return JSONResponse(payload)
        except Exception:
            return JSONResponse(
                {"error": "frontend_push_module_unavailable"},
                status_code=503,
            )

    @app.get("/api/frontend/modules/macro-data")
    def frontend_macro_data_module(tab: str = "gdp") -> JSONResponse:
        """返回 Macro Data 模块元数据。

        Args:
            tab: 当前分类子标签。

        Returns:
            前端可渲染的模块元数据 JSON。
        """
        try:
            return JSONResponse(macro_service.build_module_payload(tab=tab))
        except MacroDataValidationError:
            return JSONResponse({"error": "invalid_macro_data_tab"}, status_code=400)
        except Exception:
            logger.exception("frontend macro data module failed")
            return JSONResponse({"error": "frontend_macro_data_module_unavailable"}, status_code=503)

    @app.get("/api/frontend/modules/macro-data/charts/{chart_id}")
    def frontend_macro_data_chart(
        chart_id: str,
        range: str = "1y",
        start_date: str | None = None,
        end_date: str | None = None,
        frequency: str | None = None,
    ) -> JSONResponse:
        """返回 Macro Data 单张图表序列。

        Args:
            chart_id: 图表指标 ID。
            range: 时间范围类型。
            start_date: 自定义起始日期。
            end_date: 自定义结束日期。
            frequency: 数据频率。

        Returns:
            前端可渲染的图表数据 JSON。
        """
        try:
            return JSONResponse(
                macro_service.build_chart_payload(
                    chart_id,
                    range_type=range,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency,
                )
            )
        except MacroDataValidationError:
            return JSONResponse({"error": "invalid_macro_data_range"}, status_code=400)
        except Exception:
            logger.exception("frontend macro data chart failed", extra={"chart_id": chart_id})
            return JSONResponse({"error": "frontend_macro_data_chart_unavailable"}, status_code=503)

    @app.post("/api/frontend/modules/macro-data/sync/{chart_id}")
    def frontend_macro_data_sync(chart_id: str) -> JSONResponse:
        """触发单张图表的底层数据同步。

        Args:
            chart_id: 图表指标 ID。

        Returns:
            包含同步点位数量的 JSON 响应。
        """
        try:
            result = macro_service.sync_chart(chart_id)
            return JSONResponse(result)
        except MacroDataValidationError:
            return JSONResponse({"error": "invalid_macro_data_chart_id"}, status_code=400)
        except Exception:
            logger.exception("frontend macro data sync failed", extra={"chart_id": chart_id})
            return JSONResponse({"error": "frontend_macro_data_sync_failed"}, status_code=503)

    @app.get("/api/frontend/modules/market-data")
    def frontend_market_data_module(tab: str = "commodities") -> JSONResponse:
        """返回 Market Data 模块元数据。"""
        try:
            return JSONResponse(market_service.build_module_payload(tab=tab))
        except MarketDataValidationError:
            return JSONResponse({"error": "invalid_market_data_tab"}, status_code=400)
        except Exception:
            logger.exception("frontend market data module failed")
            return JSONResponse({"error": "frontend_market_data_module_unavailable"}, status_code=503)

    @app.get("/api/frontend/modules/market-data/charts/{chart_id}")
    def frontend_market_data_chart(
        chart_id: str,
        range: str = "1y",
        start_date: str | None = None,
        end_date: str | None = None,
        frequency: str | None = None,
        cities: str | None = None,
    ) -> JSONResponse:
        """返回 Market Data 单张图表序列。"""
        city_list = [c.strip() for c in cities.split(",") if c.strip()] if cities else None
        try:
            return JSONResponse(
                market_service.build_chart_payload(
                    chart_id,
                    range_type=range,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency,
                    cities=city_list,
                )
            )
        except MarketDataValidationError:
            return JSONResponse({"error": "invalid_market_data_range"}, status_code=400)
        except Exception:
            logger.exception("frontend market data chart failed", extra={"chart_id": chart_id})
            return JSONResponse({"error": "frontend_market_data_chart_unavailable"}, status_code=503)

    @app.post("/api/frontend/modules/market-data/sync/{chart_id}")
    def frontend_market_data_sync(chart_id: str) -> JSONResponse:
        """触发单张图表的底层数据同步。"""
        try:
            result = market_service.sync_chart(chart_id)
            return JSONResponse(result)
        except MarketDataValidationError:
            return JSONResponse({"error": "invalid_market_data_chart_id"}, status_code=400)
        except Exception:
            logger.exception("frontend market data sync failed", extra={"chart_id": chart_id})
            return JSONResponse({"error": "frontend_market_data_sync_failed"}, status_code=503)

    @app.get("/api/frontend/modules/event-outlook")
    def frontend_event_outlook_module(
        region: str = "domestic",
        start_date: str | None = None,
        end_date: str | None = None,
        refresh: bool = False,
    ) -> JSONResponse:
        """返回 Event Outlook 时间轴模块数据。"""
        try:
            return JSONResponse(
                event_service.build_timeline_payload(
                    region=region,
                    start_date=start_date,
                    end_date=end_date,
                    refresh=refresh,
                )
            )
        except EventOutlookValidationError:
            return JSONResponse({"error": "invalid_event_outlook_range"}, status_code=400)
        except Exception:
            logger.exception("frontend event outlook module failed", extra={"region": region})
            return JSONResponse({"error": "frontend_event_outlook_module_unavailable"}, status_code=503)

    @app.post("/api/frontend/modules/event-outlook/events")
    def frontend_event_outlook_create_event(payload: dict | None = None) -> JSONResponse:
        """手工新增 Event Outlook 时间轴事件。"""
        try:
            return JSONResponse(event_service.create_timeline_event(payload), status_code=201)
        except EventOutlookValidationError:
            return JSONResponse({"error": "invalid_event_outlook_payload"}, status_code=400)
        except Exception:
            logger.exception("frontend event outlook create failed")
            return JSONResponse({"error": "frontend_event_outlook_create_failed"}, status_code=503)

    @app.put("/api/frontend/modules/event-outlook/events/{event_id}")
    def frontend_event_outlook_update_event(event_id: int, payload: dict | None = None) -> JSONResponse:
        """编辑 Event Outlook 时间轴事件标题和摘要。"""
        try:
            return JSONResponse(event_service.update_timeline_event(event_id, payload))
        except EventOutlookValidationError:
            return JSONResponse({"error": "invalid_event_outlook_payload"}, status_code=400)
        except Exception:
            logger.exception("frontend event outlook update failed", extra={"event_id": event_id})
            return JSONResponse({"error": "frontend_event_outlook_update_failed"}, status_code=503)

    @app.put("/api/push/config")
    def update_push_config(payload: dict | None = None) -> JSONResponse:
        try:
            return JSONResponse(push_service.update_config(payload))
        except Exception:
            logger.exception("push config update failed")
            return JSONResponse(
                {"error": "push_config_update_failed"},
                status_code=400,
            )

    @app.post("/api/push/preview")
    def preview_push(payload: dict | None = None) -> JSONResponse:
        try:
            return JSONResponse(push_service.build_preview_response(payload))
        except Exception:
            logger.exception("push preview failed")
            return JSONResponse(
                {"error": "push_preview_failed"},
                status_code=400,
            )

    @app.post("/api/push/market-chart-refresh")
    def start_push_market_chart_refresh(payload: dict | None = None) -> JSONResponse:
        """启动 Push preview 当前选择范围的宽基指数历史刷新任务。"""
        try:
            return JSONResponse(push_service.start_market_chart_refresh(payload), status_code=202)
        except Exception:
            logger.exception("push market chart refresh start failed")
            return JSONResponse({"error": "push_market_chart_refresh_start_failed"}, status_code=400)

    @app.get("/api/push/market-chart-refresh/{job_id}")
    def get_push_market_chart_refresh(job_id: str) -> JSONResponse:
        """返回 Push preview 宽基指数历史刷新进度。"""
        try:
            return JSONResponse(push_service.get_market_chart_refresh(job_id))
        except KeyError:
            return JSONResponse({"error": "push_market_chart_refresh_not_found"}, status_code=404)
        except Exception:
            logger.exception("push market chart refresh status failed", extra={"job_id": job_id})
            return JSONResponse({"error": "push_market_chart_refresh_status_failed"}, status_code=400)

    @app.post("/api/push/trigger")
    def trigger_push(payload: dict | None = None) -> JSONResponse:
        try:
            response = push_service.trigger_push(payload)
            return JSONResponse(response, status_code=200 if response.get("ok") else 502)
        except Exception:
            logger.exception("push trigger failed")
            return JSONResponse(
                {"error": "push_trigger_failed"},
                status_code=400,
            )

    @app.get("/")
    def homepage() -> Response:
        if spa_assets.is_available:
            return RedirectResponse(url="/push")
        return build_spa_unavailable_response(spa_assets)

    def workbench_spa_entry() -> Response:
        if spa_assets.is_available:
            return FileResponse(spa_assets.index_path)
        return build_spa_unavailable_response(spa_assets)

    for route_path in WORKBENCH_ROUTES:
        app.add_api_route(route_path, workbench_spa_entry, methods=["GET"], response_class=HTMLResponse)

    @app.get("/{_:path}", response_class=HTMLResponse)
    def not_found(_: str) -> HTMLResponse:
        return HTMLResponse(
            render_error_html("Page not found", "The requested dashboard route does not exist."),
            status_code=404,
        )

    return app
