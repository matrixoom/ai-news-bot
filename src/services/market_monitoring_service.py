"""Market model monitoring service."""
from datetime import UTC, date, datetime
from typing import Callable, Dict, Sequence

from ..domain.market_monitoring import (
    FishbowlState,
    MarketModelView,
    MarketMonitoringSnapshot,
    TrackedIndexDefinition,
    build_default_market_registry,
)
from ..providers import MarketDataProvider


class MarketMonitoringService:
    """Compute reproducible market model states from provider snapshots."""

    def __init__(
        self,
        *,
        market_provider: MarketDataProvider,
        registry: Dict[str, TrackedIndexDefinition] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._market_provider = market_provider
        self._registry = registry or build_default_market_registry()
        self._now_factory = now_factory or (lambda: datetime.now(UTC))

    def build_snapshot(self, symbols: Sequence[str] | None = None, trade_date: date | None = None) -> MarketMonitoringSnapshot:
        """Build one market monitoring snapshot."""
        current_time = self._now_factory()
        effective_symbols = list(symbols or self._registry.keys())
        effective_trade_date = trade_date or current_time.date()
        snapshots = self._market_provider.fetch_index_snapshots(
            symbols=effective_symbols,
            trade_date=effective_trade_date,
        )
        snapshots_by_symbol = {snapshot.symbol: snapshot for snapshot in snapshots}

        items = [
            self._build_market_view(self._registry[symbol], snapshots_by_symbol.get(symbol), effective_trade_date)
            for symbol in effective_symbols
        ]
        return MarketMonitoringSnapshot(
            generated_at=current_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
            items=items,
        )

    def _build_market_view(self, definition: TrackedIndexDefinition, snapshot, trade_date: date) -> MarketModelView:
        if snapshot is None:
            return MarketModelView(
                key=definition.symbol,
                label=definition.display_name,
                trade_date=trade_date.isoformat(),
                close_value="暂无数据",
                ma20_value="暂无数据",
                deviation_pct="暂无数据",
                fishbowl_state=FishbowlState.UNAVAILABLE,
                explanation="该指数暂无可用数据源返回。",
                source_label=definition.source_label,
                status="unavailable",
            )

        closes = [*snapshot.lookback_closes, snapshot.close_price]
        if len(closes) < 20:
            return MarketModelView(
                key=definition.symbol,
                label=definition.display_name,
                trade_date=snapshot.trade_date.isoformat(),
                close_value=f"{snapshot.close_price:.1f}",
                ma20_value="暂无数据",
                deviation_pct="暂无数据",
                fishbowl_state=FishbowlState.UNAVAILABLE,
                explanation="历史回看数据不足，无法计算 MA20。",
                source_label=definition.source_label,
                status="degraded",
            )

        ma20 = sum(closes[-20:]) / 20
        deviation_pct = ((snapshot.close_price - ma20) / ma20) * 100
        state = self._resolve_fishbowl_state(deviation_pct)
        explanation = self._explain_state(state, deviation_pct)
        return MarketModelView(
            key=definition.symbol,
            label=definition.display_name,
            trade_date=snapshot.trade_date.isoformat(),
            close_value=f"{snapshot.close_price:.1f}",
            ma20_value=f"{ma20:.1f}",
            deviation_pct=f"{deviation_pct:+.1f}%",
            fishbowl_state=state,
            explanation=explanation,
            source_label=definition.source_label,
            status="live",
        )

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
            return f"价格显著高于 MA20（{deviation_pct:+.1f}%），处于明显突破状态。"
        if state == FishbowlState.CONSTRUCTIVE:
            return f"价格维持在 MA20 上方（{deviation_pct:+.1f}%），鱼缸状态保持偏强。"
        if state == FishbowlState.NEUTRAL:
            return f"价格小幅低于 MA20（{deviation_pct:+.1f}%），接近鱼缸边界。"
        return f"价格明显低于 MA20（{deviation_pct:+.1f}%），鱼缸模型显示压力较大。"
