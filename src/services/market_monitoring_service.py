"""Market model monitoring service."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Callable, Dict, Sequence

from ..domain.external_data import MarketIndexHistoryPoint
from ..domain.market_monitoring import (
    FishbowlState,
    MarketChartPoint,
    MarketModelView,
    MarketMonitoringSnapshot,
    TrackedIndexDefinition,
    build_default_market_registry,
)
from ..providers import MarketDataProvider, ProviderAvailability
from .market_history_store import MarketHistoryStore, MarketSyncState, StoredMarketPoint


class MarketMonitoringService:
    """Compute reproducible market model states from persisted market history."""

    def __init__(
        self,
        *,
        market_provider: MarketDataProvider,
        store: MarketHistoryStore | None = None,
        registry: Dict[str, TrackedIndexDefinition] | None = None,
        now_factory: Callable[[], datetime] | None = None,
        history_window_days: int = 180,
        fallback_window_days: int = 30,
    ) -> None:
        self._market_provider = market_provider
        self._store = store or MarketHistoryStore()
        self._registry = registry or build_default_market_registry()
        self._now_factory = now_factory or (lambda: datetime.now(UTC))
        self._history_window_days = history_window_days
        self._fallback_window_days = fallback_window_days

    def build_snapshot(
        self,
        symbols: Sequence[str] | None = None,
        trade_date: date | None = None,
        *,
        refresh_store: bool = False,
    ) -> MarketMonitoringSnapshot:
        """Build one market monitoring snapshot from the SQLite-backed history store."""
        current_time = self._now_factory()
        effective_symbols = list(symbols or self._registry.keys())
        effective_trade_date = trade_date or current_time.date()
        self._repair_mixed_sample_history(symbols=effective_symbols)

        if refresh_store:
            self.refresh_store(symbols=list(effective_symbols), trade_date=effective_trade_date)

        items = [
            self._build_market_view(
                definition=self._registry[symbol],
                points=self._store.load_points(
                    symbol=symbol,
                    end_date=effective_trade_date,
                    window_days=self._history_window_days,
                ),
                sync_state=self._store.get_sync_state(symbol),
                trade_date=effective_trade_date,
            )
            for symbol in effective_symbols
        ]
        return MarketMonitoringSnapshot(
            generated_at=current_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
            items=items,
        )

    def refresh_store(self, *, symbols: Sequence[str], trade_date: date) -> None:
        """Refresh persisted market history for the requested symbols."""
        requested = [symbol for symbol in symbols if symbol in self._registry]
        if not requested:
            return

        synced_at = self._now_factory().isoformat(timespec="seconds").replace("+00:00", "Z")
        provider_status = self._market_provider.healthcheck()
        snapshots = self._market_provider.fetch_index_snapshots(symbols=requested, trade_date=trade_date)
        snapshots_by_symbol = {snapshot.symbol: snapshot for snapshot in snapshots}

        for symbol in requested:
            definition = self._registry[symbol]
            snapshot = snapshots_by_symbol.get(symbol)
            if snapshot is None:
                self._store.upsert_symbol_status(
                    symbol=symbol,
                    display_name=definition.display_name,
                    currency=definition.currency,
                    provider_key=getattr(self._market_provider, "provider_key", "unknown-market-provider"),
                    source_url="",
                    status="unavailable",
                    warning_message="未获取到最新市场数据，请核对数据源状态。",
                    synced_at=synced_at,
                )
                continue

            if self._is_sample_snapshot(snapshot) and self._store.has_non_sample_history(symbol):
                self._store.purge_sample_rows_if_mixed(
                    symbol=symbol,
                    warning_message="已忽略样例刷新结果，保留上次实盘历史。",
                    synced_at=synced_at,
                )
                self._store.upsert_symbol_status(
                    symbol=symbol,
                    display_name=definition.display_name,
                    currency=definition.currency,
                    provider_key=snapshot.provider,
                    source_url=snapshot.source_url,
                    status="degraded",
                    warning_message="当前仅拿到样例数据，为避免污染历史库，已保留上次实盘历史。",
                    synced_at=synced_at,
                )
                continue

            if not self._is_sample_snapshot(snapshot):
                self._store.purge_sample_rows_if_mixed(
                    symbol=symbol,
                    warning_message="已移除混入的样例数据，当前仅保留实盘历史。",
                    synced_at=synced_at,
                )

            points, normalization_warning = self._normalize_snapshot_points(snapshot)
            window_label, coverage_warning = self._resolve_history_window(points)
            warnings = [normalization_warning, coverage_warning]
            if provider_status.availability != ProviderAvailability.LIVE and provider_status.detail:
                warnings.append(provider_status.detail)
            warning_message = " ".join(part for part in warnings if part).strip()
            status = self._resolve_snapshot_status(
                provider_status=provider_status,
                point_count=len(points),
                warning_message=warning_message,
            )
            self._store.upsert_symbol_history(
                symbol=symbol,
                display_name=definition.display_name,
                currency=snapshot.currency or definition.currency,
                provider_key=snapshot.provider,
                source_url=snapshot.source_url,
                points=points,
                status=status,
                window_label=window_label,
                warning_message=warning_message,
                synced_at=synced_at,
            )

    def _repair_mixed_sample_history(self, *, symbols: Sequence[str]) -> None:
        synced_at = self._now_factory().isoformat(timespec="seconds").replace("+00:00", "Z")
        for symbol in symbols:
            self._store.purge_sample_rows_if_mixed(
                symbol=symbol,
                warning_message="已移除混入的样例数据，当前仅保留实盘历史。",
                synced_at=synced_at,
            )

    def _build_market_view(
        self,
        *,
        definition: TrackedIndexDefinition,
        points: Sequence[StoredMarketPoint],
        sync_state: MarketSyncState | None,
        trade_date: date,
    ) -> MarketModelView:
        if not points:
            warning = sync_state.warning_message if sync_state else ""
            explanation = warning or "该指数暂时没有可用的历史收盘数据。"
            return MarketModelView(
                key=definition.symbol,
                label=definition.display_name,
                trade_date=trade_date.isoformat(),
                close_value="暂无数据",
                ma20_value="暂无数据",
                deviation_pct="暂无数据",
                fishbowl_state=FishbowlState.UNAVAILABLE,
                explanation=explanation,
                source_label=definition.source_label,
                status="unavailable",
                data_window_label=sync_state.window_label if sync_state else "",
                history_warning=warning,
                chart_points=[],
            )

        chart_points = self._build_chart_points(points)
        latest_raw = points[-1]
        latest_chart = chart_points[-1]
        warning = sync_state.warning_message if sync_state else ""
        status = sync_state.status if sync_state else "live"

        if latest_chart.ma20_price is None or latest_chart.deviation_pct is None:
            explanation = "历史数据不足 20 个交易点，暂时无法计算 M20 与乖离率。"
            if warning:
                explanation = f"{explanation} {warning}"
            return MarketModelView(
                key=definition.symbol,
                label=definition.display_name,
                trade_date=latest_raw.trade_date.isoformat(),
                close_value=f"{latest_raw.close_price:.1f}",
                ma20_value="暂无数据",
                deviation_pct="暂无数据",
                fishbowl_state=FishbowlState.UNAVAILABLE,
                explanation=explanation,
                source_label=definition.source_label,
                status="degraded" if status != "sample" else "sample",
                data_window_label=sync_state.window_label if sync_state else "",
                history_warning=warning,
                chart_points=chart_points,
            )

        deviation_pct = latest_chart.deviation_pct
        state = self._resolve_fishbowl_state(deviation_pct)
        explanation = self._explain_state(state, deviation_pct)
        if warning:
            explanation = f"{explanation} {warning}"
        return MarketModelView(
            key=definition.symbol,
            label=definition.display_name,
            trade_date=latest_raw.trade_date.isoformat(),
            close_value=f"{latest_raw.close_price:.1f}",
            ma20_value=f"{latest_chart.ma20_price:.1f}",
            deviation_pct=f"{deviation_pct:+.1f}%",
            fishbowl_state=state,
            explanation=explanation,
            source_label=definition.source_label,
            status=status,
            data_window_label=sync_state.window_label if sync_state else "",
            history_warning=warning,
            chart_points=chart_points,
        )

    def _build_chart_points(self, points: Sequence[StoredMarketPoint]) -> list[MarketChartPoint]:
        chart_points: list[MarketChartPoint] = []
        closes = [point.close_price for point in points]
        for index, point in enumerate(points):
            ma20_price: float | None = None
            deviation_pct: float | None = None
            if index >= 19:
                window = closes[index - 19:index + 1]
                ma20_price = sum(window) / 20
                deviation_pct = ((point.close_price - ma20_price) / ma20_price) * 100 if ma20_price else None
            chart_points.append(
                MarketChartPoint(
                    trade_date=point.trade_date.isoformat(),
                    close_price=round(point.close_price, 4),
                    ma20_price=round(ma20_price, 4) if ma20_price is not None else None,
                    deviation_pct=round(deviation_pct, 4) if deviation_pct is not None else None,
                    volume=round(point.volume, 4) if isinstance(point.volume, (int, float)) else None,
                )
            )
        return chart_points

    def _normalize_snapshot_points(self, snapshot) -> tuple[list[MarketIndexHistoryPoint], str]:
        if getattr(snapshot, "history_points", ()):
            history_points = list(snapshot.history_points)
            warning = ""
        else:
            history_points = self._infer_history_points(snapshot)
            warning = "历史日期由旧版回看窗口反推，精度有限，请复核。"

        current_volume = getattr(snapshot, "volume", None)
        existing_current = next((point for point in history_points if point.trade_date == snapshot.trade_date), None)
        if current_volume is None and existing_current is not None:
            current_volume = getattr(existing_current, "volume", None)

        history_points.append(
            MarketIndexHistoryPoint(
                trade_date=snapshot.trade_date,
                close_price=float(snapshot.close_price),
                volume=float(current_volume) if isinstance(current_volume, (int, float)) else None,
            )
        )

        points_by_date: dict[date, MarketIndexHistoryPoint] = {}
        for point in history_points:
            points_by_date[point.trade_date] = MarketIndexHistoryPoint(
                trade_date=point.trade_date,
                close_price=float(point.close_price),
                volume=float(point.volume) if isinstance(point.volume, (int, float)) else None,
            )
        ordered = sorted(points_by_date.values(), key=lambda item: item.trade_date)
        return ordered, warning

    def _infer_history_points(self, snapshot) -> list[MarketIndexHistoryPoint]:
        if not getattr(snapshot, "lookback_closes", ()):
            return []
        inferred: list[MarketIndexHistoryPoint] = []
        cursor = snapshot.trade_date
        for close in reversed(snapshot.lookback_closes):
            cursor = self._previous_trading_day(cursor)
            inferred.append(
                MarketIndexHistoryPoint(
                    trade_date=cursor,
                    close_price=float(close),
                    volume=None,
                )
            )
        inferred.reverse()
        return inferred

    def _is_sample_snapshot(self, snapshot) -> bool:
        provider_key = str(getattr(snapshot, "provider", "") or "").strip().lower()
        return provider_key.startswith("sample-")

    def _resolve_history_window(self, points: Sequence[MarketIndexHistoryPoint]) -> tuple[str, str]:
        if not points:
            return "", "未拉取到可用历史序列。"
        coverage_days = (points[-1].trade_date - points[0].trade_date).days
        if coverage_days >= self._history_window_days - 15:
            return "近6个月", ""
        if coverage_days >= 75:
            return "近3个月", "仅拉取到近3个月数据，未完整覆盖近6个月。"
        if coverage_days >= self._fallback_window_days - 10:
            return "近1个月", "仅拉取到近1个月数据，未完整覆盖近3个月和近6个月。"
        return f"近{coverage_days + 1}天", "历史窗口不足1个月，结果可能不稳定。"

    def _resolve_snapshot_status(self, *, provider_status, point_count: int, warning_message: str) -> str:
        provider_key = getattr(provider_status, "provider_key", "")
        if point_count <= 0:
            return "unavailable"
        if provider_key.startswith("sample-"):
            return "sample"
        if provider_status.availability == ProviderAvailability.UNAVAILABLE:
            return "unavailable"
        if point_count < 20:
            return "degraded"
        if provider_status.availability == ProviderAvailability.DEGRADED:
            return "degraded"
        if warning_message:
            return "degraded"
        return "live"

    def _previous_trading_day(self, anchor: date) -> date:
        candidate = anchor - timedelta(days=1)
        while candidate.weekday() >= 5:
            candidate -= timedelta(days=1)
        return candidate

    def _resolve_fishbowl_state(self, deviation_pct: float) -> FishbowlState:
        if deviation_pct >= 3:
            return FishbowlState.BREAKOUT
        if deviation_pct >= 0:
            return FishbowlState.CONSTRUCTIVE
        if deviation_pct >= -3:
            return FishbowlState.NEUTRAL
        return FishbowlState.PRESSURED

    def _explain_state(self, state: FishbowlState, deviation_pct: float) -> str:
        if state == FishbowlState.BREAKOUT:
            return f"价格显著高于 M20（{deviation_pct:+.1f}%），处于明显突破状态。"
        if state == FishbowlState.CONSTRUCTIVE:
            return f"价格维持在 M20 上方（{deviation_pct:+.1f}%），结构仍偏强。"
        if state == FishbowlState.NEUTRAL:
            return f"价格小幅低于 M20（{deviation_pct:+.1f}%），接近模型平衡区。"
        return f"价格明显低于 M20（{deviation_pct:+.1f}%），模型显示承压。"
