"""Macro indicator monitoring service backed by SQLite history."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Callable, Dict, Sequence

from ..domain.macro_monitoring import (
    MacroIndicatorDefinition,
    MacroIndicatorView,
    MacroMonitoringSnapshot,
    MacroSeriesPointView,
    TrendDirection,
    build_default_macro_registry,
)
from ..providers import MacroDataProvider, ProviderAvailability
from .macro_history_store import MacroHistoryStore, MacroSyncState, StoredMacroPoint


class MacroMonitoringService:
    """Build macro views from persisted historical indicator series."""

    def __init__(
        self,
        *,
        macro_provider: MacroDataProvider,
        store: MacroHistoryStore | None = None,
        registry: Dict[str, MacroIndicatorDefinition] | None = None,
        now_factory: Callable[[], datetime] | None = None,
        history_window_days: int = 400,
    ) -> None:
        self._macro_provider = macro_provider
        self._store = store or MacroHistoryStore()
        self._registry = registry or build_default_macro_registry()
        self._now_factory = now_factory or (lambda: datetime.now(UTC))
        self._history_window_days = history_window_days

    def build_snapshot(
        self,
        indicator_codes: Sequence[str] | None = None,
        *,
        refresh_store: bool = False,
    ) -> MacroMonitoringSnapshot:
        """Build one macro-monitoring snapshot across selected indicator codes."""
        current_time = self._now_factory()
        effective_codes = [code for code in (indicator_codes or self._registry.keys()) if code in self._registry]
        start_date = current_time.date() - timedelta(days=self._history_window_days)

        if refresh_store or self._needs_initial_sync(effective_codes):
            self.refresh_store(indicator_codes=effective_codes, start_date=start_date)

        indicators = [
            self._build_indicator_view(
                definition=self._registry[code],
                points=self._store.load_points(indicator_code=code, start_date=start_date),
                sync_state=self._store.get_sync_state(code),
            )
            for code in effective_codes
        ]
        return MacroMonitoringSnapshot(
            generated_at=current_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
            indicators=indicators,
        )

    def refresh_store(self, *, indicator_codes: Sequence[str], start_date: date) -> None:
        """Refresh persisted macro history for the requested indicators."""
        requested = [code for code in indicator_codes if code in self._registry]
        if not requested:
            return

        synced_at = self._now_factory().isoformat(timespec="seconds").replace("+00:00", "Z")
        provider_status = self._macro_provider.healthcheck()
        series_items = self._macro_provider.fetch_history_series(indicator_codes=requested, start_date=start_date)
        series_by_code = {item.indicator_code: item for item in series_items}

        for code in requested:
            definition = self._registry[code]
            series = series_by_code.get(code)
            if series is None or not series.points:
                self._store.upsert_indicator_status(
                    indicator_code=code,
                    provider_key=getattr(self._macro_provider, "provider_key", "unknown-macro-provider"),
                    source_url=definition.source_url,
                    status="unavailable",
                    warning_message="数据源未返回可用历史序列。",
                    synced_at=synced_at,
                )
                continue

            status = self._resolve_series_status(provider_status=provider_status, provider_key=series.provider)
            warning = provider_status.detail if provider_status.availability != ProviderAvailability.LIVE else ""
            self._store.upsert_indicator_history(
                indicator_code=code,
                provider_key=series.provider,
                source_url=series.source_url or definition.source_url,
                points=series.points,
                status=status,
                warning_message=warning,
                synced_at=synced_at,
            )

    def _needs_initial_sync(self, indicator_codes: Sequence[str]) -> bool:
        for code in indicator_codes:
            sync_state = self._store.get_sync_state(code)
            if sync_state is None or sync_state.point_count <= 0:
                return True
        return False

    def _build_indicator_view(
        self,
        *,
        definition: MacroIndicatorDefinition,
        points: Sequence[StoredMacroPoint],
        sync_state: MacroSyncState | None,
    ) -> MacroIndicatorView:
        if not points:
            return MacroIndicatorView(
                key=definition.indicator_code,
                label=definition.display_name,
                value="暂无数据",
                previous_value="暂无数据",
                change_label="等待数据源返回。",
                trend=TrendDirection.UNAVAILABLE,
                source_label=definition.source_label,
                source_url=definition.source_url,
                updated_at="暂无数据",
                period_label="暂无数据",
                frequency=definition.frequency,
                context=(sync_state.warning_message if sync_state and sync_state.warning_message else definition.update_rule),
                unit=definition.unit,
                pair_key=definition.pair_key,
                status="unavailable",
            )

        latest = points[-1]
        previous = points[-2] if len(points) > 1 else None
        trend = self._resolve_trend(latest=latest, previous=previous)
        return MacroIndicatorView(
            key=definition.indicator_code,
            label=definition.display_name,
            value=self._format_value(latest.value, latest.unit),
            previous_value=self._format_optional_value(previous.value if previous else None, latest.unit),
            change_label=self._build_change_label(latest=latest, previous=previous, definition=definition),
            trend=trend,
            source_label=definition.source_label,
            source_url=sync_state.source_url if sync_state and sync_state.source_url else definition.source_url,
            updated_at=latest.released_at or (sync_state.synced_at if sync_state else "暂无数据"),
            period_label=latest.period_label,
            frequency=definition.frequency,
            context=self._build_context(definition=definition, sync_state=sync_state),
            unit=latest.unit,
            pair_key=definition.pair_key,
            status=sync_state.status if sync_state else "live",
            numeric_value=latest.value,
            history_points=[
                MacroSeriesPointView(
                    period_end=point.period_end.isoformat(),
                    period_label=point.period_label,
                    value=round(point.value, 4),
                )
                for point in points
            ],
        )

    def _build_context(self, *, definition: MacroIndicatorDefinition, sync_state: MacroSyncState | None) -> str:
        detail = sync_state.warning_message.strip() if sync_state and sync_state.warning_message else ""
        if detail:
            return f"{definition.display_hint} {detail}".strip()
        return definition.display_hint

    def _format_optional_value(self, value: float | None, unit: str) -> str:
        if value is None:
            return "暂无数据"
        return self._format_value(value, unit)

    def _format_value(self, value: float, unit: str) -> str:
        if unit == "%":
            return f"{value:.1f}%"
        if unit == "pct":
            return f"{value:.2f}%"
        if unit == "tn yuan":
            return f"{value:.2f} 万亿元"
        if unit == "ratio":
            return f"{value:.4f}"
        if unit == "CNY/USD":
            return f"{value:.4f}"
        text = f"{value:.2f}".rstrip("0").rstrip(".")
        return f"{text} {unit}".strip()

    def _build_change_label(
        self,
        *,
        latest: StoredMacroPoint,
        previous: StoredMacroPoint | None,
        definition: MacroIndicatorDefinition,
    ) -> str:
        if previous is None:
            return f"最新期: {latest.period_label}"
        delta = latest.value - previous.value
        prefix = {
            "daily": "较前一交易日",
            "monthly": "较上月",
            "quarterly": "较上季",
            "yearly": "较上年",
        }.get(definition.frequency.value, "较上一期")
        if definition.unit == "%":
            return f"{prefix}: {delta:+.1f} 个百分点"
        if definition.unit == "pct":
            return f"{prefix}: {delta:+.2f} 个百分点"
        if definition.unit == "tn yuan":
            return f"{prefix}: {delta:+.2f} 万亿元"
        if definition.unit == "ratio":
            return f"{prefix}: {delta:+.4f}"
        if definition.unit == "CNY/USD":
            return f"{prefix}: {delta:+.4f}"
        return f"{prefix}: {delta:+.2f}"

    def _resolve_trend(self, *, latest: StoredMacroPoint, previous: StoredMacroPoint | None) -> TrendDirection:
        if previous is None:
            return TrendDirection.UNAVAILABLE
        if latest.value > previous.value:
            return TrendDirection.UP
        if latest.value < previous.value:
            return TrendDirection.DOWN
        return TrendDirection.FLAT

    def _resolve_series_status(self, *, provider_status, provider_key: str) -> str:
        if str(provider_key).startswith("sample-"):
            return "sample"
        if provider_status.availability == ProviderAvailability.UNAVAILABLE:
            return "unavailable"
        if provider_status.availability == ProviderAvailability.DEGRADED:
            return "degraded"
        return "live"
