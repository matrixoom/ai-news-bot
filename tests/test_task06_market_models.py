from datetime import UTC, date, datetime, timedelta
from contextlib import contextmanager
from pathlib import Path
import shutil
import unittest
from uuid import uuid4

from src.domain import FishbowlState, build_default_market_registry
from src.domain.external_data import MarketIndexHistoryPoint, MarketIndexSnapshot
from src.providers import ProviderAvailability, ProviderStatus
from src.services.market_history_store import MarketHistoryStore
from src.services.market_monitoring_service import MarketMonitoringService


def build_history(trade_date: date, *, days: int, start_value: float, step: float) -> tuple[MarketIndexHistoryPoint, ...]:
    points: list[MarketIndexHistoryPoint] = []
    cursor = trade_date - timedelta(days=days + 40)
    value = start_value
    while cursor < trade_date:
        if cursor.weekday() < 5:
            points.append(MarketIndexHistoryPoint(trade_date=cursor, close_price=round(value, 2)))
            value += step
        cursor += timedelta(days=1)
    return tuple(points)


@contextmanager
def isolated_market_store() -> MarketHistoryStore:
    root = Path(".data/.test-market-history")
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / f"market-{uuid4().hex}.db"
    store = MarketHistoryStore(db_path)
    try:
        yield store
    finally:
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(f"{db_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)


class FakeMarketProvider:
    provider_key = "fake-market"

    def __init__(self, snapshots, *, availability: ProviderAvailability = ProviderAvailability.LIVE, detail: str = "ok"):
        self._snapshots = {snapshot.symbol: snapshot for snapshot in snapshots}
        self._availability = availability
        self._detail = detail
        self.calls = 0

    def fetch_index_snapshots(self, *, symbols, trade_date):
        _ = trade_date
        self.calls += 1
        return [self._snapshots[symbol] for symbol in symbols if symbol in self._snapshots]

    def healthcheck(self):
        return ProviderStatus(self.provider_key, self._availability, self._detail, "2026-03-15T00:00:00Z")


class Task06DocumentationTests(unittest.TestCase):
    def test_task06_main_doc_links_protocol_and_tests(self):
        with open("TASK/06-market-models-and-daily-dashboard.md", encoding="utf-8") as handle:
            content = handle.read()

        self.assertIn("Completed for implementation phase.", content)
        self.assertIn("06-fishbowl-rules-and-panel-protocol.md", content)
        self.assertIn("tests/test_task06_market_models.py", content)


class MarketHistoryStoreTests(unittest.TestCase):
    def test_store_upserts_same_symbol_trade_date_without_duplicates(self):
        with isolated_market_store() as store:
            first_points = (
                MarketIndexHistoryPoint(trade_date=date(2026, 3, 14), close_price=100.0),
                MarketIndexHistoryPoint(trade_date=date(2026, 3, 15), close_price=101.0),
            )
            second_points = (
                MarketIndexHistoryPoint(trade_date=date(2026, 3, 15), close_price=105.0),
            )

            store.upsert_symbol_history(
                symbol="CSI300",
                display_name="沪深 300",
                currency="CNY",
                provider_key="fake-market",
                source_url="https://example.com",
                points=first_points,
                status="live",
                window_label="近1个月",
                warning_message="",
                synced_at="2026-03-15T08:00:00Z",
            )
            store.upsert_symbol_history(
                symbol="CSI300",
                display_name="沪深 300",
                currency="CNY",
                provider_key="fake-market",
                source_url="https://example.com",
                points=second_points,
                status="live",
                window_label="近1个月",
                warning_message="",
                synced_at="2026-03-15T09:00:00Z",
            )

            points = store.load_latest_points(symbol="CSI300", limit=10)
            sync_state = store.get_sync_state("CSI300")

        self.assertEqual(len(points), 2)
        self.assertEqual(points[-1].close_price, 105.0)
        self.assertIsNotNone(sync_state)
        self.assertEqual(sync_state.point_count, 2)


class MarketMonitoringServiceTests(unittest.TestCase):
    def test_registry_covers_default_indices(self):
        registry = build_default_market_registry()
        self.assertEqual(set(registry), {"CSI300", "CSI500", "CSI1000", "SSE", "CHINEXT", "HSTECH"})

    def test_service_refreshes_store_and_builds_three_month_history_chart(self):
        trade_date = date(2026, 3, 20)
        history = build_history(trade_date, days=90, start_value=100.0, step=0.8)
        provider = FakeMarketProvider(
            [
                MarketIndexSnapshot(
                    provider="fake-market",
                    symbol="CSI300",
                    display_name="CSI 300",
                    trade_date=trade_date,
                    close_price=history[-1].close_price + 5.0,
                    currency="CNY",
                    source_url="https://example.com",
                    lookback_closes=tuple(point.close_price for point in history[-19:]),
                    history_points=history,
                )
            ]
        )

        with isolated_market_store() as store:
            service = MarketMonitoringService(
                market_provider=provider,
                store=store,
                registry={"CSI300": build_default_market_registry()["CSI300"]},
                now_factory=lambda: datetime(2026, 3, 20, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(["CSI300"], trade_date, refresh_store=True)
            item = snapshot.items[0]

        self.assertEqual(provider.calls, 1)
        self.assertEqual(item.status, "degraded")
        self.assertEqual(item.data_window_label, "近3个月")
        self.assertEqual(item.fishbowl_state, FishbowlState.BREAKOUT)
        self.assertIn("近6个月", item.history_warning)
        self.assertGreater(len(item.chart_points), 40)
        self.assertNotEqual(item.ma20_value, "暂无数据")
        self.assertTrue(any(point.ma20_price is not None for point in item.chart_points))

    def test_service_prefers_six_month_window_when_available(self):
        trade_date = date(2026, 3, 20)
        history = build_history(trade_date, days=180, start_value=180.0, step=0.5)
        provider = FakeMarketProvider(
            [
                MarketIndexSnapshot(
                    provider="fake-market",
                    symbol="CSI300",
                    display_name="CSI 300",
                    trade_date=trade_date,
                    close_price=history[-1].close_price + 2.0,
                    currency="CNY",
                    source_url="https://example.com",
                    history_points=history,
                )
            ]
        )

        with isolated_market_store() as store:
            service = MarketMonitoringService(
                market_provider=provider,
                store=store,
                registry={"CSI300": build_default_market_registry()["CSI300"]},
                now_factory=lambda: datetime(2026, 3, 20, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(["CSI300"], trade_date, refresh_store=True)
            item = snapshot.items[0]

        self.assertEqual(item.data_window_label, "近6个月")
        self.assertEqual(item.history_warning, "")
        self.assertGreater(len(item.chart_points), 100)

    def test_service_falls_back_to_one_month_window_and_warns(self):
        trade_date = date(2026, 3, 20)
        history = build_history(trade_date, days=30, start_value=200.0, step=0.5)
        provider = FakeMarketProvider(
            [
                MarketIndexSnapshot(
                    provider="fake-market",
                    symbol="CSI300",
                    display_name="CSI 300",
                    trade_date=trade_date,
                    close_price=history[-1].close_price + 1.0,
                    currency="CNY",
                    source_url="https://example.com",
                    history_points=history,
                )
            ]
        )

        with isolated_market_store() as store:
            service = MarketMonitoringService(
                market_provider=provider,
                store=store,
                registry={"CSI300": build_default_market_registry()["CSI300"]},
                now_factory=lambda: datetime(2026, 3, 20, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(["CSI300"], trade_date, refresh_store=True)
            item = snapshot.items[0]

        self.assertEqual(item.data_window_label, "近1个月")
        self.assertIn("近1个月", item.history_warning)
        self.assertEqual(item.status, "degraded")

    def test_service_reads_from_existing_sqlite_without_refetching(self):
        trade_date = date(2026, 3, 20)
        history = build_history(trade_date, days=180, start_value=300.0, step=0.6)
        provider = FakeMarketProvider(
            [
                MarketIndexSnapshot(
                    provider="fake-market",
                    symbol="CSI300",
                    display_name="CSI 300",
                    trade_date=trade_date,
                    close_price=history[-1].close_price + 2.0,
                    currency="CNY",
                    source_url="https://example.com",
                    history_points=history,
                )
            ]
        )

        with isolated_market_store() as store:
            store.upsert_symbol_history(
                symbol="CSI300",
                display_name="沪深 300",
                currency="CNY",
                provider_key="fake-market",
                source_url="https://example.com",
                points=history,
                status="live",
                window_label="近6个月",
                warning_message="",
                synced_at="2026-03-20T08:00:00Z",
            )
            service = MarketMonitoringService(
                market_provider=provider,
                store=store,
                registry={"CSI300": build_default_market_registry()["CSI300"]},
                now_factory=lambda: datetime(2026, 3, 20, tzinfo=UTC),
            )

            first = service.build_snapshot(["CSI300"], trade_date)
            second = service.build_snapshot(["CSI300"], trade_date)

        self.assertEqual(provider.calls, 0)
        self.assertEqual(first.items[0].trade_date, second.items[0].trade_date)
        self.assertEqual(first.items[0].close_value, second.items[0].close_value)

    def test_service_repairs_mixed_sample_and_live_history_before_rendering(self):
        trade_date = date(2026, 3, 22)
        live_history = build_history(date(2026, 3, 20), days=180, start_value=4500.0, step=1.2)
        provider = FakeMarketProvider([])

        with isolated_market_store() as store:
            store.upsert_symbol_history(
                symbol="CSI300",
                display_name="沪深 300",
                currency="CNY",
                provider_key="akshare-market",
                source_url="https://example.com/live",
                points=live_history,
                status="live",
                window_label="近3个月",
                warning_message="",
                synced_at="2026-03-20T08:00:00Z",
            )
            store.upsert_symbol_history(
                symbol="CSI300",
                display_name="沪深 300",
                currency="CNY",
                provider_key="sample-market",
                source_url="https://example.com/sample",
                points=(MarketIndexHistoryPoint(trade_date=trade_date, close_price=3632.0),),
                status="sample",
                window_label="近1个月",
                warning_message="样例数据",
                synced_at="2026-03-22T08:00:00Z",
            )
            service = MarketMonitoringService(
                market_provider=provider,
                store=store,
                registry={"CSI300": build_default_market_registry()["CSI300"]},
                now_factory=lambda: datetime(2026, 3, 22, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(["CSI300"], trade_date)
            points = store.load_latest_points(symbol="CSI300", limit=3)

        self.assertEqual(snapshot.items[0].trade_date, live_history[-1].trade_date.isoformat())
        self.assertTrue(all(point.trade_date.isoformat() != "2026-03-22" for point in points))
        self.assertIn("已移除混入的样例数据", snapshot.items[0].history_warning)

    def test_force_refresh_ignores_sample_snapshot_when_live_history_exists(self):
        trade_date = date(2026, 3, 22)
        live_history = build_history(date(2026, 3, 20), days=180, start_value=4500.0, step=1.2)
        provider = FakeMarketProvider(
            [
                MarketIndexSnapshot(
                    provider="sample-market",
                    symbol="CSI300",
                    display_name="CSI 300",
                    trade_date=trade_date,
                    close_price=3632.0,
                    currency="CNY",
                    source_url="https://example.com/sample",
                )
            ],
            availability=ProviderAvailability.DEGRADED,
            detail="样例数据",
        )

        with isolated_market_store() as store:
            store.upsert_symbol_history(
                symbol="CSI300",
                display_name="沪深 300",
                currency="CNY",
                provider_key="akshare-market",
                source_url="https://example.com/live",
                points=live_history,
                status="live",
                window_label="近3个月",
                warning_message="",
                synced_at="2026-03-20T08:00:00Z",
            )
            service = MarketMonitoringService(
                market_provider=provider,
                store=store,
                registry={"CSI300": build_default_market_registry()["CSI300"]},
                now_factory=lambda: datetime(2026, 3, 22, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(["CSI300"], trade_date, refresh_store=True)
            latest = store.load_latest_points(symbol="CSI300", limit=1)[0]

        self.assertEqual(provider.calls, 1)
        self.assertEqual(latest.trade_date.isoformat(), live_history[-1].trade_date.isoformat())
        self.assertEqual(snapshot.items[0].trade_date, live_history[-1].trade_date.isoformat())
        self.assertIn("保留上次实盘历史", snapshot.items[0].history_warning)

    def test_legacy_lookback_only_snapshots_are_marked_uncertain(self):
        trade_date = date(2026, 3, 20)
        provider = FakeMarketProvider(
            [
                MarketIndexSnapshot(
                    provider="fake-market",
                    symbol="CSI300",
                    display_name="CSI 300",
                    trade_date=trade_date,
                    close_price=110.0,
                    currency="CNY",
                    source_url="https://example.com",
                    lookback_closes=tuple([100.0 + index for index in range(19)]),
                )
            ]
        )

        with isolated_market_store() as store:
            service = MarketMonitoringService(
                market_provider=provider,
                store=store,
                registry={"CSI300": build_default_market_registry()["CSI300"]},
                now_factory=lambda: datetime(2026, 3, 20, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(["CSI300"], trade_date, refresh_store=True)
            item = snapshot.items[0]

        self.assertEqual(item.status, "degraded")
        self.assertIn("反推", item.history_warning)
        self.assertEqual(len(item.chart_points), 20)

    def test_missing_symbol_does_not_break_other_cards(self):
        provider = FakeMarketProvider([])

        with isolated_market_store() as store:
            service = MarketMonitoringService(
                market_provider=provider,
                store=store,
                registry={
                    "CSI300": build_default_market_registry()["CSI300"],
                    "HSTECH": build_default_market_registry()["HSTECH"],
                },
                now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(["CSI300", "HSTECH"], date(2026, 3, 15))

        self.assertEqual(provider.calls, 0)
        self.assertEqual(len(snapshot.items), 2)
        self.assertEqual(snapshot.items[0].status, "unavailable")
        self.assertEqual(snapshot.items[1].status, "unavailable")


if __name__ == "__main__":
    unittest.main()
