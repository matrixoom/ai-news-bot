"""Macro indicator monitoring service."""
from datetime import UTC, datetime
from typing import Callable, Dict, Iterable, List, Sequence

from ..domain.external_data import MacroIndicatorReading
from ..domain.macro_monitoring import (
    MacroIndicatorDefinition,
    MacroIndicatorView,
    MacroMonitoringSnapshot,
    MacroFrequency,
    TrendDirection,
    build_default_macro_registry,
)
from ..providers import MacroDataProvider


class MacroMonitoringService:
    """Build dashboard-facing macro indicator cards from provider data."""

    def __init__(
        self,
        *,
        macro_provider: MacroDataProvider,
        registry: Dict[str, MacroIndicatorDefinition] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._macro_provider = macro_provider
        self._registry = registry or build_default_macro_registry()
        self._now_factory = now_factory or (lambda: datetime.now(UTC))

    def build_snapshot(self, indicator_codes: Sequence[str] | None = None) -> MacroMonitoringSnapshot:
        """Build one macro-monitoring snapshot across selected indicator codes."""
        current_time = self._now_factory()
        selected_codes = list(indicator_codes or self._registry.keys())
        readings = self._macro_provider.fetch_latest_readings(indicator_codes=selected_codes)
        readings_by_code = {reading.indicator_code: reading for reading in readings}

        indicators = [
            self._build_indicator_view(
                definition=self._registry[code],
                reading=readings_by_code.get(code),
            )
            for code in selected_codes
        ]
        return MacroMonitoringSnapshot(
            generated_at=current_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
            indicators=indicators,
        )

    def _build_indicator_view(
        self,
        *,
        definition: MacroIndicatorDefinition,
        reading: MacroIndicatorReading | None,
    ) -> MacroIndicatorView:
        if reading is None:
            return MacroIndicatorView(
                key=definition.indicator_code,
                label=definition.display_name,
                value="Unavailable",
                previous_value="Unavailable",
                change_label="Waiting for provider data",
                trend=TrendDirection.UNAVAILABLE,
                source_label=definition.source_label,
                updated_at="Unavailable",
                frequency=definition.frequency,
                context=definition.update_rule,
                status="unavailable",
            )

        trend = self._resolve_trend(reading)
        return MacroIndicatorView(
            key=definition.indicator_code,
            label=definition.display_name,
            value=self._format_value(reading.value, reading.unit),
            previous_value=self._format_optional_value(reading.previous_value, reading.unit),
            change_label=self._build_change_label(reading),
            trend=trend,
            source_label=definition.source_label,
            updated_at=reading.released_at,
            frequency=definition.frequency,
            context=reading.trend_summary or definition.display_hint,
            status="live",
        )

    def _format_optional_value(self, value: float | None, unit: str) -> str:
        if value is None:
            return "Unavailable"
        return self._format_value(value, unit)

    def _format_value(self, value: float, unit: str) -> str:
        if unit == "%":
            return f"{value:.1f}%"
        if unit == "tn yuan":
            return f"{value:.1f} tn yuan"
        text = f"{value:.2f}".rstrip("0").rstrip(".")
        return f"{text} {unit}".strip()

    def _build_change_label(self, reading: MacroIndicatorReading) -> str:
        if reading.change_value is not None and reading.change_kind:
            change_value = self._format_signed_change(reading.change_value, reading.unit)
            return f"{reading.change_kind}: {change_value}"
        if reading.previous_value is not None:
            return f"Previous: {self._format_value(reading.previous_value, reading.unit)}"
        return "Change unavailable"

    def _format_signed_change(self, value: float, unit: str) -> str:
        sign = "+" if value > 0 else ""
        if unit == "%":
            return f"{sign}{value:.1f} pct"
        return f"{sign}{value:.2f}".rstrip("0").rstrip(".")

    def _resolve_trend(self, reading: MacroIndicatorReading) -> TrendDirection:
        if reading.trend_summary:
            lowered = reading.trend_summary.lower()
            if "up" in lowered or "rise" in lowered or "accelerat" in lowered:
                return TrendDirection.UP
            if "down" in lowered or "declin" in lowered or "cool" in lowered or "ease" in lowered:
                return TrendDirection.DOWN
            if "flat" in lowered or "stable" in lowered:
                return TrendDirection.FLAT

        if reading.change_value is not None:
            if reading.change_value > 0:
                return TrendDirection.UP
            if reading.change_value < 0:
                return TrendDirection.DOWN
            return TrendDirection.FLAT

        if reading.previous_value is not None:
            if reading.value > reading.previous_value:
                return TrendDirection.UP
            if reading.value < reading.previous_value:
                return TrendDirection.DOWN
            return TrendDirection.FLAT

        return TrendDirection.UNAVAILABLE
