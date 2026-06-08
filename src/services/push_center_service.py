"""Push center service for configurable previews, delivery, and schedules."""
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import threading
from typing import Any, Iterable, Mapping
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..notifiers import EmailNotifier
from .dashboard_service import DashboardSection, DashboardService, DashboardSnapshot, SummaryBlock
from .push_market_chart_range import DEFAULT_PUSH_MARKET_CHART_RANGE, resolve_push_market_chart_range
from .push_report_service import PushReportService


logger = logging.getLogger(__name__)

SUPPORTED_CHANNEL_TYPES = (
    {
        "id": "email",
        "label": "邮箱",
        "enabled": True,
        "description": "SMTP 邮件推送，适合作为日报和定时推送首个渠道。",
    },
    {
        "id": "webhook",
        "label": "Webhook",
        "enabled": False,
        "description": "预留给后续渠道扩展。",
    },
)

AVAILABLE_SOURCE_MODULES = (
    {
        "id": "market",
        "label": "市场模型",
        "enabled": True,
        "push_ready": True,
        "description": "当前最适合日报推送的模块。",
    },
    {
        "id": "macro",
        "label": "宏观指标",
        "enabled": False,
        "push_ready": False,
        "description": "已预留扩展位，暂不推荐用于日报。",
    },
    {
        "id": "news",
        "label": "新闻情报",
        "enabled": False,
        "push_ready": False,
        "description": "已预留扩展位，暂不推荐用于日报。",
    },
    {
        "id": "events",
        "label": "事件展望",
        "enabled": False,
        "push_ready": False,
        "description": "已预留扩展位，暂不推荐用于日报。",
    },
)

STYLE_OPTIONS = (
    {
        "id": "newspaper",
        "label": "报刊双栏",
        "recommended": True,
        "description": "左右分栏，适合晨报和盘中快照。",
    },
    {
        "id": "briefing",
        "label": "简报单栏",
        "recommended": False,
        "description": "更紧凑，适合快速浏览。",
    },
)

DEFAULT_TIMEZONE = "Asia/Shanghai"
MAX_RECENT_RUNS = 12
MAX_SCHEDULER_HISTORY = 128
DEFAULT_MARKET_CHART_REFRESH_TOTAL = 6
MARKET_CHART_REFRESH_TERMINAL_STATUSES = {"completed", "completed_with_warnings", "failed"}
DEFAULT_PUSH_CONFIG = {
    "selected_module_ids": ["market"],
    "report_style": "newspaper",
    "market_chart_range": DEFAULT_PUSH_MARKET_CHART_RANGE,
    "email": {
        "enabled": True,
        "label": "Primary Email",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "use_tls": True,
        "username": "",
        "password": "",
        "from_address": "",
        "to_addresses": "",
    },
    "schedules": [
        {
            "id": "market-daily",
            "name": "市场日报",
            "enabled": True,
            "module_ids": ["market"],
            "channel_types": ["email"],
            "times": ["08:00", "12:05", "17:00"],
            "timezone": DEFAULT_TIMEZONE,
        }
    ],
}
DEFAULT_PUSH_STATE = {"scheduler_history": {}}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class PushCenterService:
    """Owns push-center config, previews, manual delivery, and schedule execution."""

    def __init__(
        self,
        *,
        dashboard_service: DashboardService | None = None,
        report_service: PushReportService | None = None,
        config_path: str | Path | None = None,
        enable_scheduler: bool = False,
        scheduler_check_seconds: float | None = None,
        email_notifier_factory=EmailNotifier,
    ) -> None:
        self._dashboard_service = dashboard_service or DashboardService()
        self._report_service = report_service or PushReportService()
        self._email_notifier_factory = email_notifier_factory
        self._config_path = Path(
            config_path or os.getenv("PUSH_CENTER_CONFIG_PATH", ".data/push_center.json")
        )
        self._state_path = self._config_path.with_name(
            f"{self._config_path.stem}.state{self._config_path.suffix}"
        )
        self._schedule_claim_root = self._config_path.with_name(
            f"{self._config_path.stem}.schedule-claims"
        )
        self._template_path = self._config_path.with_name(
            f"{self._config_path.stem}.template{self._config_path.suffix}"
        )
        self._log_root = self._config_path.parent / "logs" / self._config_path.stem
        self._config_lock = threading.Lock()
        self._scheduler_check_seconds = max(
            5.0,
            float(
                scheduler_check_seconds
                if scheduler_check_seconds is not None
                else os.getenv("PUSH_CENTER_SCHEDULER_CHECK_SECONDS", "20")
            ),
        )
        self._frontend_auto_refresh_ms = max(
            5000,
            int(os.getenv("PUSH_FRONTEND_AUTO_REFRESH_MS", "30000")),
        )
        self._scheduler_stop_event = threading.Event()
        self._scheduler_thread: threading.Thread | None = None
        self._market_chart_refresh_lock = threading.Lock()
        self._market_chart_refresh_jobs: dict[str, dict[str, Any]] = {}
        self._market_chart_refresh_thread: threading.Thread | None = None
        self._ensure_config_file()
        if enable_scheduler:
            self.start_scheduler()

    @property
    def frontend_auto_refresh_ms(self) -> int:
        return self._frontend_auto_refresh_ms

    def build_module_payload(
        self,
        *,
        force_refresh_preview: bool = False,
        include_preview: bool = True,
    ) -> dict[str, Any]:
        config = self._load_config()
        preview = (
            self._build_preview(config, force_refresh=force_refresh_preview)
            if include_preview
            else self._empty_preview(config, error="preview_not_requested")
        )
        recent_runs = self._read_recent_runs()
        note = f"{len(config['schedules'])} 个任务 / {len(config['selected_module_ids'])} 个模块"
        return {
            "generated_at": _utc_now_iso(),
            "module": {
                "id": "push",
                "label": "推送中心",
                "note": note,
                "description": "配置邮件推送、预览日报样式，并管理定时任务。",
                "status": self._module_status(config, preview),
                "loading": False,
                "details": [
                    {
                        "id": "workspace",
                        "label": "推送配置",
                        "kind": "push",
                        "note": note,
                        "section": {
                            "channel_type_options": list(SUPPORTED_CHANNEL_TYPES),
                            "source_module_options": list(AVAILABLE_SOURCE_MODULES),
                            "style_options": list(STYLE_OPTIONS),
                            "config_path": str(self._config_path),
                            "config": self._public_config(config),
                            "preview": preview,
                            "recent_runs": recent_runs,
                            "scheduler": {
                                "enabled": self._scheduler_thread is not None,
                                "check_interval_seconds": self._scheduler_check_seconds,
                            },
                        },
                    }
                ],
            },
        }

    def should_serve_loading_module(self) -> tuple[bool, str]:
        config = self._load_config()
        selected_modules = list(config.get("selected_module_ids") or ["market"])
        should_serve = getattr(self._dashboard_service, "should_serve_loading_module", None)
        get_state = getattr(self._dashboard_service, "get_module_bootstrap_state", None)
        if not callable(should_serve):
            return False, ""
        for module_id in selected_modules:
            if not should_serve(module_id):
                continue
            detail = ""
            if callable(get_state):
                _, detail = get_state(module_id)
            return True, detail or "后台正在拉取最新数据。"
        return False, ""

    def update_config(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        payload = self._unwrap_payload(payload)
        existing = self._load_config()
        normalized = self._normalize_config(payload or {}, base=existing)
        self._save_config(normalized)
        return self.build_module_payload(force_refresh_preview=True)

    def build_preview_response(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        request_payload = payload
        payload = self._unwrap_payload(payload)
        existing = self._load_config()
        normalized = self._normalize_config(payload or {}, base=existing)
        refresh_data = True
        if isinstance(request_payload, Mapping) and "refresh_data" in request_payload:
            refresh_data = bool(request_payload.get("refresh_data"))
        return {
            "generated_at": _utc_now_iso(),
            "config": self._public_config(normalized),
            "preview": self._build_preview(normalized, force_refresh=refresh_data),
        }

    def start_market_chart_refresh(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        """启动当前草稿范围对应的宽基指数历史刷新任务。

        Args:
            payload: 当前 Push Center 草稿配置，可带 `config` 包装层。

        Returns:
            可供前端轮询的刷新任务摘要。
        """
        payload = self._unwrap_payload(payload)
        existing = self._load_config()
        normalized = self._normalize_config(payload or {}, base=existing)
        with self._market_chart_refresh_lock:
            for existing_job in self._market_chart_refresh_jobs.values():
                if existing_job["status"] not in MARKET_CHART_REFRESH_TERMINAL_STATUSES:
                    return {"job": self._public_market_chart_refresh_job(existing_job)}
            job_id = uuid4().hex
            job = {
                "id": job_id,
                "status": "pending",
                "completed": 0,
                "total": DEFAULT_MARKET_CHART_REFRESH_TOTAL,
                "percentage": 0,
                "current_symbol": "",
                "current_label": "",
                "message": "刷新任务已创建，正在准备拉取宽基指数历史。",
                "errors": [],
                "preview": None,
                "_config": normalized,
            }
            self._market_chart_refresh_jobs[job_id] = job
            self._market_chart_refresh_thread = threading.Thread(
                target=self._run_market_chart_refresh,
                args=(job_id,),
                name=f"push-market-chart-refresh-{job_id[:8]}",
                daemon=True,
            )
            self._market_chart_refresh_thread.start()
            return {"job": self._public_market_chart_refresh_job(job)}

    def get_market_chart_refresh(self, job_id: str) -> dict[str, Any]:
        """读取宽基指数图表刷新任务状态。

        Args:
            job_id: 启动接口返回的任务标识。

        Returns:
            可公开给前端的任务状态。

        Raises:
            KeyError: 任务不存在。
        """
        with self._market_chart_refresh_lock:
            job = self._market_chart_refresh_jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return {"job": self._public_market_chart_refresh_job(job)}

    def trigger_push(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """触发手动发送；若请求携带了与当前配置一致的预览，则直接复用该预览。"""
        request_payload = payload
        payload = self._unwrap_payload(payload)
        existing = self._load_config()
        normalized = self._normalize_config(payload or {}, base=existing)
        persist = bool((payload or {}).get("persist"))
        requested_preview = self._resolve_requested_preview(request_payload, config=normalized)
        result = self._execute_delivery(
            normalized,
            trigger="manual",
            job_name="手动触发",
            preview_payload=requested_preview,
        )
        if persist:
            self._save_config(normalized)
        return result

    def run_due_jobs(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        config = self._load_config()
        state = self._load_state()
        current_time = now or datetime.now(UTC)
        results: list[dict[str, Any]] = []
        dirty = False
        for schedule in config.get("schedules", []):
            if not schedule.get("enabled"):
                continue
            if not self._is_schedule_due(schedule, current_time, state):
                continue
            if not self._claim_schedule_slot(schedule, current_time):
                continue
            run_result = self._execute_delivery(
                config,
                trigger="scheduled",
                job_name=str(schedule.get("name") or "定时推送"),
                module_ids=schedule.get("module_ids") or config.get("selected_module_ids"),
                channel_types=schedule.get("channel_types") or ["email"],
                execution_timezone=str(schedule.get("timezone") or DEFAULT_TIMEZONE),
                executed_now=current_time,
            )
            schedule_key = self._schedule_history_key(schedule, current_time)
            state.setdefault("scheduler_history", {})[schedule_key] = run_result["result"]["executed_at"]
            dirty = True
            results.append(run_result)
        if dirty:
            self._trim_scheduler_history(state)
            self._save_state(state)
        return results

    def start_scheduler(self) -> None:
        if self._scheduler_thread is not None:
            return
        self._scheduler_stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="push-center-scheduler",
            daemon=True,
        )
        self._scheduler_thread.start()

    def stop_scheduler(self) -> None:
        self._scheduler_stop_event.set()
        if self._scheduler_thread is not None:
            self._scheduler_thread.join(timeout=2.0)
            self._scheduler_thread = None
        if self._market_chart_refresh_thread is not None:
            self._market_chart_refresh_thread.join(timeout=2.0)
            self._market_chart_refresh_thread = None

    def _scheduler_loop(self) -> None:
        while not self._scheduler_stop_event.wait(self._scheduler_check_seconds):
            try:
                self.run_due_jobs()
            except Exception as error:  # pragma: no cover - defensive background logging
                logger.warning("push-center scheduler loop failed: %s", error)

    def _run_market_chart_refresh(self, job_id: str) -> None:
        """执行宽基指数全量刷新，并基于新缓存重绘当前预览。"""
        with self._market_chart_refresh_lock:
            job = self._market_chart_refresh_jobs[job_id]
            config = deepcopy(job["_config"])
            job["status"] = "running"
        try:
            range_spec = resolve_push_market_chart_range(config.get("market_chart_range"))
            rebuild_market_module = getattr(self._dashboard_service, "rebuild_market_module", None)
            if callable(rebuild_market_module):
                rebuild_market_module(
                    history_window_days=range_spec.window_days,
                    progress_callback=lambda event: self._update_market_chart_refresh_progress(job_id, event)
                )
            else:
                self._dashboard_service.build_market_module(
                    force_refresh=True,
                    history_window_days=range_spec.window_days,
                )
            preview = self._build_preview(config, force_refresh=False)
            with self._market_chart_refresh_lock:
                job = self._market_chart_refresh_jobs[job_id]
                job["preview"] = preview
                job["completed"] = job["total"]
                job["percentage"] = 100
                if job["errors"]:
                    job["status"] = "completed_with_warnings"
                    job["message"] = "图表已重绘，但部分指数刷新失败，已保留上次可用历史。"
                else:
                    job["status"] = "completed"
                    job["message"] = f"{range_spec.label}宽基指数历史已刷新，预览图已重绘。"
        except Exception as error:  # pragma: no cover - defensive background logging
            logger.exception("push market chart refresh failed", extra={"job_id": job_id})
            with self._market_chart_refresh_lock:
                job = self._market_chart_refresh_jobs[job_id]
                job["status"] = "failed"
                job["message"] = f"图表刷新失败：{error}"
                job["errors"].append(str(error))

    def _update_market_chart_refresh_progress(self, job_id: str, event: Mapping[str, Any]) -> None:
        """接收市场服务逐指数事件，并更新可轮询任务状态。"""
        with self._market_chart_refresh_lock:
            job = self._market_chart_refresh_jobs[job_id]
            completed = max(0, int(event.get("completed") or 0))
            total = max(1, int(event.get("total") or job["total"]))
            job["status"] = "running"
            job["completed"] = min(completed, total)
            job["total"] = total
            job["percentage"] = round((job["completed"] / total) * 100)
            job["current_symbol"] = str(event.get("symbol") or "")
            job["current_label"] = str(event.get("label") or "")
            job["message"] = str(event.get("message") or "正在刷新宽基指数历史。")
            if event.get("status") == "failed":
                error_message = f"{job['current_label'] or job['current_symbol']}: {job['message']}"
                if error_message not in job["errors"]:
                    job["errors"].append(error_message)

    def _public_market_chart_refresh_job(self, job: Mapping[str, Any]) -> dict[str, Any]:
        """移除内部草稿配置，仅返回前端需要的任务字段。"""
        return {
            key: deepcopy(value)
            for key, value in job.items()
            if not str(key).startswith("_")
        }

    def _legacy_broken_build_preview(
        self,
        config: Mapping[str, Any],
        *,
        module_ids: Iterable[str] | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        selected_modules = list(module_ids or config.get("selected_module_ids") or ["market"])
        try:
            market_chart_range = str(config.get("market_chart_range") or DEFAULT_PUSH_MARKET_CHART_RANGE)
            snapshot = self._build_push_snapshot(
                selected_modules,
                force_refresh=force_refresh,
                market_chart_range=market_chart_range,
            )
            subject = self._build_subject(snapshot, config, selected_modules)
            text_body = self._report_service.build_markdown(
                snapshot,
                module_ids=selected_modules,
                market_chart_range=market_chart_range,
            )
            html_body = self._report_service.build_email_html(
                snapshot,
                module_ids=selected_modules,
                layout=str(config.get("report_style") or "newspaper"),
                market_chart_range=market_chart_range,
            )
            return {
                "ok": True,
                "generated_at": snapshot.generated_at,
                "subject": subject,
                "text_body": text_body,
                "html_body": html_body,
                "style": config.get("report_style") or "newspaper",
                "selected_module_ids": selected_modules,
            }
        except Exception as error:
            return {
                "ok": False,
                "generated_at": _utc_now_iso(),
                "subject": "鎺ㄩ€侀瑙堜笉鍙敤",
                "text_body": "",
                "html_body": "",
                "style": config.get("report_style") or "newspaper",
                "selected_module_ids": selected_modules,
                "error": str(error),
            }

    def _legacy_broken_empty_preview(
        self,
        config: Mapping[str, Any],
        *,
        module_ids: Iterable[str] | None = None,
        error: str,
    ) -> dict[str, Any]:
        selected_modules = list(module_ids or config.get("selected_module_ids") or ["market"])
        return {
            "ok": False,
            "generated_at": _utc_now_iso(),
            "subject": "",
            "text_body": "",
            "html_body": "",
            "style": config.get("report_style") or "newspaper",
            "selected_module_ids": selected_modules,
            "error": error,
        }

    def _legacy_broken_build_push_snapshot(
        self,
        selected_modules: Iterable[str],
        *,
        force_refresh: bool,
        market_chart_range: str,
    ) -> DashboardSnapshot:
        # 鎺ㄩ€侀瑙堝彧闇€瑕佸凡閫夋ā鍧楋紝閬垮厤鏅€氶〉闈㈠姞杞借鏁村紶 dashboard 鐨勫叏閲忔瀯寤烘嫋鎱€?        module_ids = [str(module_id).strip().lower() for module_id in selected_modules if str(module_id).strip()]
        if not module_ids:
            module_ids = ["market"]
        if not self._can_build_push_snapshot_from_modules(module_ids):
            return self._dashboard_service.build_snapshot(force_refresh=force_refresh)

        generated_at = _utc_now_iso()
        summary = SummaryBlock(
            title="财经与政策情报仪表盘",
            subtitle="推送预览仅构建已选模块，减少与无关模块的额外开销。",
            as_of_label=generated_at,
            coverage_note="",
            highlights=[],
        )
        sections: list[DashboardSection] = []
        news_sections = []
        macro_sections = []
        market_sections = []
        event_sections = []

        for module_id in module_ids:
            if module_id == "news":
                _, _, news_sections, news_status = self._dashboard_service.build_news_module(
                    force_refresh=force_refresh,
                )
                sections.append(DashboardSection("news", "新闻情报", news_status.status, news_status.detail))
                continue
            if module_id == "macro":
                _, macro_sections = self._dashboard_service.build_macro_module(force_refresh=force_refresh)
                sections.append(DashboardSection("macro", "宏观指标", "live", "push-preview"))
                continue
            if module_id == "market":
                range_spec = resolve_push_market_chart_range(market_chart_range)
                _, market_sections = self._dashboard_service.build_market_module(
                    force_refresh=force_refresh,
                    history_window_days=range_spec.window_days,
                )
                sections.append(DashboardSection("market", "市场模型", "live", "push-preview"))
                continue
            if module_id == "events":
                _, event_sections = self._dashboard_service.build_events_module(force_refresh=force_refresh)
                sections.append(DashboardSection("events", "事件与政策展望", "live", "push-preview"))

        return DashboardSnapshot(
            generated_at=generated_at,
            news_mode="hybrid",
            title=summary.title,
            summary=summary.subtitle,
            sections=sections,
            dashboard_summary=summary,
            news_sections=news_sections,
            macro_sections=macro_sections,
            market_sections=market_sections,
            event_sections=event_sections,
            data_status=[],
        )

    def _legacy_broken_can_build_push_snapshot_from_modules(self, module_ids: list[str]) -> bool:
        builder_names = {
            "news": "build_news_module",
            "macro": "build_macro_module",
            "market": "build_market_module",
            "events": "build_events_module",
        }
        return all(
            callable(getattr(self._dashboard_service, builder_names.get(module_id, ""), None))
            for module_id in module_ids
        )

    def _build_preview(
        self,
        config: Mapping[str, Any],
        *,
        module_ids: Iterable[str] | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        selected_modules = list(module_ids or config.get("selected_module_ids") or ["market"])
        try:
            market_chart_range = str(config.get("market_chart_range") or DEFAULT_PUSH_MARKET_CHART_RANGE)
            snapshot = self._build_push_snapshot(
                selected_modules,
                force_refresh=force_refresh,
                market_chart_range=market_chart_range,
            )
            subject = self._build_subject(snapshot, config, selected_modules)
            text_body = self._report_service.build_markdown(
                snapshot,
                module_ids=selected_modules,
                market_chart_range=market_chart_range,
            )
            html_body = self._report_service.build_email_html(
                snapshot,
                module_ids=selected_modules,
                layout=str(config.get("report_style") or "newspaper"),
                market_chart_range=market_chart_range,
            )
            return {
                "ok": True,
                "generated_at": snapshot.generated_at,
                "subject": subject,
                "text_body": text_body,
                "html_body": html_body,
                "style": config.get("report_style") or "newspaper",
                "market_chart_range": resolve_push_market_chart_range(config.get("market_chart_range")).value,
                "selected_module_ids": selected_modules,
            }
        except Exception as error:
            return self._empty_preview(config, module_ids=selected_modules, error=str(error))

    def _empty_preview(
        self,
        config: Mapping[str, Any],
        *,
        module_ids: Iterable[str] | None = None,
        error: str,
    ) -> dict[str, Any]:
        selected_modules = list(module_ids or config.get("selected_module_ids") or ["market"])
        return {
            "ok": False,
            "generated_at": _utc_now_iso(),
            "subject": "",
            "text_body": "",
            "html_body": "",
            "style": config.get("report_style") or "newspaper",
            "market_chart_range": resolve_push_market_chart_range(config.get("market_chart_range")).value,
            "selected_module_ids": selected_modules,
            "error": error,
        }

    def _build_push_snapshot(
        self,
        selected_modules: Iterable[str],
        *,
        force_refresh: bool,
        market_chart_range: str,
    ) -> DashboardSnapshot:
        module_ids = [str(module_id).strip().lower() for module_id in selected_modules if str(module_id).strip()]
        if not module_ids:
            module_ids = ["market"]
        if not self._can_build_push_snapshot_from_modules(module_ids):
            return self._dashboard_service.build_snapshot(force_refresh=force_refresh)

        generated_at = _utc_now_iso()
        summary = SummaryBlock(
            title="\u8d22\u7ecf\u4e0e\u653f\u7b56\u60c5\u62a5\u4eea\u8868\u76d8",
            subtitle="\u63a8\u9001\u9884\u89c8\u4ec5\u6784\u5efa\u5df2\u9009\u6a21\u5757\uff0c\u51cf\u5c11\u4e0e\u65e0\u5173\u6a21\u5757\u7684\u989d\u5916\u5f00\u9500\u3002",
            as_of_label=generated_at,
            coverage_note="",
            highlights=[],
        )
        sections: list[DashboardSection] = []
        news_sections = []
        macro_sections = []
        market_sections = []
        event_sections = []

        for module_id in module_ids:
            if module_id == "news":
                _, _, news_sections, news_status = self._dashboard_service.build_news_module(
                    force_refresh=force_refresh,
                )
                sections.append(
                    DashboardSection(
                        "news",
                        "\u65b0\u95fb\u60c5\u62a5",
                        news_status.status,
                        news_status.detail,
                    )
                )
                continue
            if module_id == "macro":
                _, macro_sections = self._dashboard_service.build_macro_module(force_refresh=force_refresh)
                sections.append(DashboardSection("macro", "\u5b8f\u89c2\u6307\u6807", "live", "push-preview"))
                continue
            if module_id == "market":
                range_spec = resolve_push_market_chart_range(market_chart_range)
                _, market_sections = self._dashboard_service.build_market_module(
                    force_refresh=force_refresh,
                    history_window_days=range_spec.window_days,
                )
                sections.append(DashboardSection("market", "\u5e02\u573a\u6a21\u578b", "live", "push-preview"))
                continue
            if module_id == "events":
                _, event_sections = self._dashboard_service.build_events_module(force_refresh=force_refresh)
                sections.append(DashboardSection("events", "\u4e8b\u4ef6\u4e0e\u653f\u7b56\u5c55\u671b", "live", "push-preview"))

        return DashboardSnapshot(
            generated_at=generated_at,
            news_mode="hybrid",
            title=summary.title,
            summary=summary.subtitle,
            sections=sections,
            dashboard_summary=summary,
            news_sections=news_sections,
            macro_sections=macro_sections,
            market_sections=market_sections,
            event_sections=event_sections,
            data_status=[],
        )

    def _can_build_push_snapshot_from_modules(self, module_ids: list[str]) -> bool:
        builder_names = {
            "news": "build_news_module",
            "macro": "build_macro_module",
            "market": "build_market_module",
            "events": "build_events_module",
        }
        return all(
            callable(getattr(self._dashboard_service, builder_names.get(module_id, ""), None))
            for module_id in module_ids
        )

    def _build_subject(self, snapshot, config: Mapping[str, Any], module_ids: Iterable[str]) -> str:
        module_map = {item["id"]: item["label"] for item in AVAILABLE_SOURCE_MODULES}
        module_labels = [module_map[module_id] for module_id in module_ids if module_id in module_map]
        base = self._report_service.build_subject(snapshot)
        if module_labels:
            return f"{' / '.join(module_labels)} - {base}"
        return base

    def _execute_delivery(
        self,
        config: Mapping[str, Any],
        *,
        trigger: str,
        job_name: str,
        module_ids: Iterable[str] | None = None,
        channel_types: Iterable[str] | None = None,
        execution_timezone: str | None = None,
        executed_now: datetime | None = None,
        preview_payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        selected_modules = list(module_ids or config.get("selected_module_ids") or ["market"])
        selected_channels = [str(item).strip().lower() for item in (channel_types or ["email"]) if str(item).strip()]
        preview = (
            dict(preview_payload)
            if isinstance(preview_payload, Mapping)
            else self._build_preview(
                config,
                module_ids=selected_modules,
                force_refresh=True,
            )
        )
        resolved_timezone = self._normalize_timezone(
            execution_timezone or self._default_execution_timezone(config)
        )
        executed_at = self._format_executed_at(executed_now, resolved_timezone)
        sent: list[str] = []
        failed: list[str] = []
        error_messages: list[str] = []

        if not preview.get("ok"):
            failed = list(selected_channels)
            error_messages.append(str(preview.get("error") or "preview_unavailable"))
        else:
            if "email" in selected_channels:
                email_result = self._send_email(config, subject=preview["subject"], text_body=preview["text_body"], html_body=preview["html_body"])
                if email_result is True:
                    sent.append("email")
                else:
                    failed.append("email")
                    error_messages.append(email_result)

        status = "success" if sent and not failed else "partial" if sent else "failed"
        detail = " / ".join(error_messages) if error_messages else "发送完成"
        run_record = {
            "executed_at": executed_at,
            "timezone": resolved_timezone,
            "trigger": trigger,
            "job_name": job_name,
            "status": status,
            "detail": detail,
            "subject": preview.get("subject", ""),
            "channel_types": selected_channels,
            "module_ids": selected_modules,
        }
        recent_runs = self._record_recent_run(run_record)
        if failed:
            logger.warning("push-center %s run completed with failures: %s", trigger, detail)
        else:
            logger.info("push-center %s run completed successfully", trigger)
        return {
            "ok": bool(sent),
            "preview": preview,
            "recent_runs": recent_runs,
            "result": {
                "status": status,
                "executed_at": executed_at,
                "timezone": resolved_timezone,
                "trigger": trigger,
                "job_name": job_name,
                "sent": sent,
                "failed": failed,
                "detail": detail,
            },
        }

    def _resolve_requested_preview(
        self,
        payload: Mapping[str, Any] | None,
        *,
        config: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        """仅在前端预览与当前配置一致时复用，避免页面所见与实际发送分叉。"""
        if not isinstance(payload, Mapping):
            return None
        raw_preview = payload.get("preview")
        if not isinstance(raw_preview, Mapping):
            return None

        preview_modules = self._normalize_module_ids(raw_preview.get("selected_module_ids"))
        preview_style = self._normalize_style(raw_preview.get("style"))
        try:
            preview_range = resolve_push_market_chart_range(raw_preview.get("market_chart_range")).value
        except ValueError:
            logger.warning("push-center ignored requested preview with invalid market_chart_range")
            return None
        config_modules = self._normalize_module_ids(config.get("selected_module_ids"))
        config_style = self._normalize_style(config.get("report_style"))
        config_range = resolve_push_market_chart_range(config.get("market_chart_range")).value
        if not bool(raw_preview.get("ok")):
            return None
        if preview_modules != config_modules or preview_style != config_style or preview_range != config_range:
            return None

        return {
            "ok": True,
            "generated_at": str(raw_preview.get("generated_at") or _utc_now_iso()),
            "subject": str(raw_preview.get("subject") or ""),
            "text_body": str(raw_preview.get("text_body") or ""),
            "html_body": str(raw_preview.get("html_body") or ""),
            "style": preview_style,
            "market_chart_range": preview_range,
            "selected_module_ids": preview_modules,
        }
    def _send_email(self, config: Mapping[str, Any], *, subject: str, text_body: str, html_body: str) -> bool | str:
        email = dict(config.get("email") or {})
        notifier = self._email_notifier_factory(
            smtp_server=email.get("smtp_server") or None,
            smtp_port=email.get("smtp_port") or None,
            smtp_use_tls=email.get("use_tls"),
            username=email.get("username") or None,
            password=email.get("password") or None,
            from_address=email.get("from_address") or None,
            email_to=email.get("to_addresses") or None,
        )
        if notifier.send(text_body, subject=subject, html_content=html_body):
            return True
        return getattr(notifier, "last_error", "") or "email_delivery_failed"

    def _module_status(self, config: Mapping[str, Any], preview: Mapping[str, Any]) -> str:
        email = config.get("email") or {}
        required = (
            email.get("smtp_server"),
            email.get("smtp_port"),
            email.get("to_addresses"),
        )
        if not all(required):
            return "degraded"
        if not preview.get("ok"):
            return "degraded"
        return "compatible"

    def _public_config(self, config: Mapping[str, Any]) -> dict[str, Any]:
        public = deepcopy(dict(config))
        email = public.setdefault("email", {})
        email["password_configured"] = bool(email.get("password"))
        return public

    def _ensure_config_file(self) -> None:
        with self._config_lock:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_template_file_locked()
            if not self._config_path.exists():
                self._write_config(DEFAULT_PUSH_CONFIG)

    def _load_config(self) -> dict[str, Any]:
        with self._config_lock:
            try:
                with self._config_path.open("r", encoding="utf-8") as handle:
                    raw = json.load(handle)
            except (FileNotFoundError, json.JSONDecodeError):
                raw = deepcopy(DEFAULT_PUSH_CONFIG)
            normalized = self._normalize_config(raw, base=DEFAULT_PUSH_CONFIG)
            self._migrate_legacy_runtime_data_locked(raw)
            return normalized

    def _save_config(self, payload: Mapping[str, Any]) -> None:
        normalized = self._normalize_config(payload, base=DEFAULT_PUSH_CONFIG)
        with self._config_lock:
            self._write_config(normalized)

    def _load_state(self) -> dict[str, Any]:
        with self._config_lock:
            return self._load_state_locked()

    def _save_state(self, payload: Mapping[str, Any]) -> None:
        normalized = self._normalize_state(payload)
        with self._config_lock:
            self._write_state(normalized)

    def _unwrap_payload(self, payload: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
        if payload is None:
            return None
        nested = payload.get("config")
        if isinstance(nested, Mapping):
            unwrapped = dict(nested)
            if "persist" in payload:
                unwrapped["persist"] = payload.get("persist")
            return unwrapped
        return payload

    def _write_config(self, payload: Mapping[str, Any]) -> None:
        self._write_json(self._config_path, payload)

    def _write_state(self, payload: Mapping[str, Any]) -> None:
        self._write_json(self._state_path, payload)

    def _write_json(self, path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(f"{path.suffix}.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        temp_path.replace(path)

    def _normalize_config(self, payload: Mapping[str, Any], *, base: Mapping[str, Any]) -> dict[str, Any]:
        merged = deepcopy(dict(base))
        if "selected_module_ids" in payload:
            merged["selected_module_ids"] = self._normalize_module_ids(payload.get("selected_module_ids"))
        else:
            merged["selected_module_ids"] = self._normalize_module_ids(merged.get("selected_module_ids"))

        merged["report_style"] = self._normalize_style(payload.get("report_style", merged.get("report_style")))
        merged["market_chart_range"] = resolve_push_market_chart_range(
            payload.get("market_chart_range", merged.get("market_chart_range"))
        ).value
        merged["email"] = self._normalize_email_config(payload.get("email", merged.get("email")))
        merged["schedules"] = self._normalize_schedules(
            payload.get("schedules", merged.get("schedules")),
            default_module_ids=merged["selected_module_ids"],
        )
        return merged

    def _normalize_state(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        state = deepcopy(DEFAULT_PUSH_STATE)
        if isinstance(payload, Mapping):
            state["scheduler_history"] = dict(payload.get("scheduler_history", {}))
        self._trim_scheduler_history(state)
        return state

    def _normalize_module_ids(self, raw_value: Any) -> list[str]:
        allowed = {item["id"] for item in AVAILABLE_SOURCE_MODULES if item["enabled"]}
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        normalized = [str(value).strip() for value in values if str(value).strip() in allowed]
        return normalized or ["market"]

    def _normalize_style(self, value: Any) -> str:
        allowed = {item["id"] for item in STYLE_OPTIONS}
        text = str(value or "").strip().lower()
        return text if text in allowed else "newspaper"

    def _normalize_email_config(self, raw_value: Any) -> dict[str, Any]:
        base = deepcopy(DEFAULT_PUSH_CONFIG["email"])
        data = dict(raw_value or {})
        base["enabled"] = bool(data.get("enabled", base["enabled"]))
        base["label"] = str(data.get("label", base["label"]) or base["label"]).strip()
        base["smtp_server"] = str(data.get("smtp_server", base["smtp_server"]) or "").strip()
        base["smtp_port"] = self._normalize_port(data.get("smtp_port", base["smtp_port"]))
        base["use_tls"] = bool(data.get("use_tls", base["use_tls"]))
        base["username"] = str(data.get("username", "") or "").strip()
        base["password"] = str(data.get("password", "") or "")
        base["from_address"] = str(data.get("from_address", "") or "").strip()
        base["to_addresses"] = str(data.get("to_addresses", "") or "").strip()
        return base

    def _normalize_port(self, value: Any) -> int:
        try:
            port = int(value)
        except (TypeError, ValueError):
            return 587
        return port if 1 <= port <= 65535 else 587

    def _normalize_schedules(self, raw_value: Any, *, default_module_ids: list[str]) -> list[dict[str, Any]]:
        schedules = raw_value if isinstance(raw_value, list) else DEFAULT_PUSH_CONFIG["schedules"]
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(schedules):
            schedule = dict(item or {})
            timezone = self._normalize_timezone(schedule.get("timezone"))
            times = self._normalize_times(schedule.get("times"))
            normalized.append(
                {
                    "id": str(schedule.get("id") or f"schedule-{index + 1}").strip(),
                    "name": str(schedule.get("name") or f"推送任务{index + 1}").strip(),
                    "enabled": bool(schedule.get("enabled", True)),
                    "module_ids": self._normalize_module_ids(schedule.get("module_ids") or default_module_ids),
                    "channel_types": self._normalize_channel_types(schedule.get("channel_types")),
                    "times": times or ["08:00"],
                    "timezone": timezone,
                }
            )
        return normalized or deepcopy(DEFAULT_PUSH_CONFIG["schedules"])

    def _normalize_channel_types(self, raw_value: Any) -> list[str]:
        allowed = {item["id"] for item in SUPPORTED_CHANNEL_TYPES if item["enabled"]}
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        normalized = [str(value).strip().lower() for value in values if str(value).strip().lower() in allowed]
        return normalized or ["email"]

    def _normalize_times(self, raw_value: Any) -> list[str]:
        values: list[str]
        if isinstance(raw_value, list):
            values = [str(item).strip() for item in raw_value]
        elif raw_value is None:
            values = []
        else:
            values = [part.strip() for part in str(raw_value).split(",")]
        normalized = [value for value in values if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value)]
        deduped: list[str] = []
        for item in normalized:
            if item not in deduped:
                deduped.append(item)
        return deduped

    def _normalize_timezone(self, value: Any) -> str:
        candidate = str(value or DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE
        try:
            ZoneInfo(candidate)
            return candidate
        except ZoneInfoNotFoundError:
            return DEFAULT_TIMEZONE

    def _normalize_recent_runs(self, raw_value: Any) -> list[dict[str, Any]]:
        runs = raw_value if isinstance(raw_value, list) else []
        normalized: list[dict[str, Any]] = []
        for item in runs[:MAX_RECENT_RUNS]:
            record = dict(item or {})
            normalized.append(
                {
                    "executed_at": str(record.get("executed_at") or _utc_now_iso()),
                    "timezone": self._normalize_timezone(record.get("timezone")),
                    "trigger": str(record.get("trigger") or "manual"),
                    "job_name": str(record.get("job_name") or "推送任务"),
                    "status": str(record.get("status") or "unknown"),
                    "detail": str(record.get("detail") or ""),
                    "subject": str(record.get("subject") or ""),
                    "channel_types": list(record.get("channel_types") or []),
                    "module_ids": list(record.get("module_ids") or []),
                }
            )
        return normalized

    def _record_recent_run(self, record: Mapping[str, Any]) -> list[dict[str, Any]]:
        normalized_items = self._normalize_recent_runs([record])
        if not normalized_items:
            return self._read_recent_runs()
        with self._config_lock:
            self._write_log_records_locked(normalized_items)
            return self._read_recent_runs_locked()

    def _read_recent_runs(self, *, limit: int = MAX_RECENT_RUNS) -> list[dict[str, Any]]:
        with self._config_lock:
            return self._read_recent_runs_locked(limit=limit)

    def _read_recent_runs_locked(self, *, limit: int = MAX_RECENT_RUNS) -> list[dict[str, Any]]:
        if limit <= 0 or not self._log_root.exists():
            return []
        records: list[dict[str, Any]] = []
        for path in self._log_root.glob("*/*/*.jsonl"):
            try:
                with path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        text = line.strip()
                        if not text:
                            continue
                        try:
                            raw = json.loads(text)
                        except json.JSONDecodeError:
                            continue
                        records.extend(self._normalize_recent_runs([raw]))
            except FileNotFoundError:
                continue
        records.sort(key=lambda item: self._parse_timestamp(item.get("executed_at")), reverse=True)
        return records[:limit]

    def _write_log_records_locked(
        self,
        records: Iterable[Mapping[str, Any]],
        *,
        dedupe: bool = False,
    ) -> None:
        grouped: dict[Path, list[dict[str, Any]]] = {}
        for record in records:
            normalized = self._normalize_recent_runs([record])
            if not normalized:
                continue
            item = normalized[0]
            grouped.setdefault(self._log_file_path(item), []).append(item)
        for path, items in grouped.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            existing_signatures: set[tuple[Any, ...]] = set()
            if dedupe and path.exists():
                try:
                    with path.open("r", encoding="utf-8") as handle:
                        for line in handle:
                            text = line.strip()
                            if not text:
                                continue
                            try:
                                raw = json.loads(text)
                            except json.JSONDecodeError:
                                continue
                            normalized_existing = self._normalize_recent_runs([raw])
                            if normalized_existing:
                                existing_signatures.add(self._recent_run_signature(normalized_existing[0]))
                except FileNotFoundError:
                    pass
            with path.open("a", encoding="utf-8") as handle:
                for item in items:
                    signature = self._recent_run_signature(item)
                    if dedupe and signature in existing_signatures:
                        continue
                    handle.write(json.dumps(item, ensure_ascii=False))
                    handle.write("\n")
                    existing_signatures.add(signature)

    def _log_file_path(self, record: Mapping[str, Any]) -> Path:
        trigger = str(record.get("trigger") or "unknown").strip().lower() or "unknown"
        executed_at = str(record.get("executed_at") or "")
        date_text = executed_at[:10] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", executed_at[:10]) else _utc_now_iso()[:10]
        month_text = date_text[:7]
        return self._log_root / trigger / month_text / f"{date_text}.jsonl"

    def _recent_run_signature(self, record: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            str(record.get("executed_at") or ""),
            str(record.get("timezone") or ""),
            str(record.get("trigger") or ""),
            str(record.get("job_name") or ""),
            str(record.get("status") or ""),
            str(record.get("detail") or ""),
            str(record.get("subject") or ""),
            tuple(record.get("channel_types") or []),
            tuple(record.get("module_ids") or []),
        )

    def _default_execution_timezone(self, config: Mapping[str, Any]) -> str:
        for schedule in config.get("schedules", []):
            if not isinstance(schedule, Mapping):
                continue
            timezone = schedule.get("timezone")
            if timezone:
                return self._normalize_timezone(timezone)
        return DEFAULT_TIMEZONE

    def _format_executed_at(self, now: datetime | None, timezone: str) -> str:
        current_time = now or datetime.now(UTC)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)
        return current_time.astimezone(ZoneInfo(timezone)).isoformat(timespec="seconds")

    def _is_schedule_due(self, schedule: Mapping[str, Any], now: datetime, state: Mapping[str, Any]) -> bool:
        timezone = ZoneInfo(str(schedule.get("timezone") or DEFAULT_TIMEZONE))
        local_now = now.astimezone(timezone)
        current_slot = local_now.strftime("%H:%M")
        if current_slot not in list(schedule.get("times") or []):
            return False
        history_key = self._schedule_history_key(schedule, now)
        return history_key not in dict(state.get("scheduler_history") or {})

    def _schedule_history_key(self, schedule: Mapping[str, Any], now: datetime) -> str:
        timezone = ZoneInfo(str(schedule.get("timezone") or DEFAULT_TIMEZONE))
        local_now = now.astimezone(timezone)
        return f"{schedule.get('id')}@{local_now.strftime('%Y-%m-%dT%H:%M')}"

    def _claim_schedule_slot(self, schedule: Mapping[str, Any], now: datetime) -> bool:
        """跨进程原子抢占计划任务的分钟槽位。

        Args:
            schedule: 当前计划任务配置。
            now: 本轮调度检查时间。

        Returns:
            当前进程首次抢占成功时返回 ``True``，槽位已被其他进程抢占时返回 ``False``。
        """

        history_key = self._schedule_history_key(schedule, now)
        claim_name = f"{hashlib.sha256(history_key.encode('utf-8')).hexdigest()}.json"
        claim_path = self._schedule_claim_root / claim_name
        self._schedule_claim_root.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(
                claim_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError:
            logger.info("push-center schedule slot already claimed: %s", history_key)
            return False
        except OSError as error:
            logger.warning(
                "push-center schedule slot claim failed for %s: %s",
                history_key,
                error,
            )
            return False

        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "history_key": history_key,
                    "claimed_at": _utc_now_iso(),
                    "process_id": os.getpid(),
                },
                handle,
                ensure_ascii=False,
            )
        return True

    def _trim_scheduler_history(self, config: dict[str, Any]) -> None:
        history = dict(config.get("scheduler_history") or {})
        if len(history) <= MAX_SCHEDULER_HISTORY:
            config["scheduler_history"] = history
            return
        sorted_items = sorted(
            history.items(),
            key=lambda item: self._parse_timestamp(item[1]),
            reverse=True,
        )
        config["scheduler_history"] = dict(sorted_items[:MAX_SCHEDULER_HISTORY])

    def _ensure_template_file_locked(self) -> None:
        if self._template_path.exists():
            return
        self._write_json(self._template_path, DEFAULT_PUSH_CONFIG)

    def _load_state_locked(self) -> dict[str, Any]:
        try:
            with self._state_path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError):
            raw = deepcopy(DEFAULT_PUSH_STATE)
        return self._normalize_state(raw)

    def _migrate_legacy_runtime_data_locked(self, raw: Any) -> None:
        if not isinstance(raw, Mapping):
            return
        needs_rewrite = False
        if "recent_runs" in raw:
            legacy_runs = self._normalize_recent_runs(raw.get("recent_runs"))
            if legacy_runs:
                self._write_log_records_locked(legacy_runs, dedupe=True)
            needs_rewrite = True
        if "scheduler_history" in raw:
            state = self._load_state_locked()
            state["scheduler_history"].update(dict(raw.get("scheduler_history") or {}))
            self._trim_scheduler_history(state)
            self._write_state(state)
            needs_rewrite = True
        if needs_rewrite:
            self._write_config(self._normalize_config(raw, base=DEFAULT_PUSH_CONFIG))

    def _parse_timestamp(self, value: Any) -> datetime:
        text = str(value or "")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return datetime.min.replace(tzinfo=UTC)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)


