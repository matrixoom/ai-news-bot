import unittest
from pathlib import Path

import pandas as pd

from src.providers.live_data import AkshareMarketDataProvider
from src.services.market_history_store import MarketHistoryStore
from src.services.market_data_repository import MarketDataRepository
from src.services.market_data_service import MarketDataService
from src.services.market_data_sync_service import _housing_points_from_frame


class MarketDataHousingTests(unittest.TestCase):
    """校验 Market Data 房价指标的多口径存储与展示。"""

    def setUp(self) -> None:
        self.db_path = Path(".tmp-events-tests") / "market-data" / f"{self.id().split('.')[-1]}.db"
        if self.db_path.exists():
            self.db_path.unlink()

    def test_housing_loader_normalizes_yoy_mom_and_derives_global_index(self) -> None:
        """校验 AkShare 100 基准指数会转换为百分比，并派生全局走势。"""
        frame = pd.DataFrame(
            [
                {
                    "日期": "2026-01-01",
                    "城市": "北京",
                    "二手住宅价格指数-同比": 110.0,
                    "二手住宅价格指数-环比": 101.0,
                },
                {
                    "日期": "2026-02-01",
                    "城市": "北京",
                    "二手住宅价格指数-同比": 80.0,
                    "二手住宅价格指数-环比": 99.0,
                },
            ]
        )

        points = _housing_points_from_frame(frame)

        values_by_metric = {(point["period_label"], point["metric"]): point["value"] for point in points}
        self.assertEqual(values_by_metric[("2026-01", "yoy")], 10.0)
        self.assertEqual(values_by_metric[("2026-01", "mom")], 1.0)
        self.assertEqual(values_by_metric[("2026-01", "global_index")], 101.0)
        self.assertAlmostEqual(values_by_metric[("2026-02", "global_index")], 99.99)

    def test_real_estate_chart_returns_yoy_mom_and_global_index_series(self) -> None:
        """校验前端房价图表同时返回同比、环比与全局走势三组序列。"""
        repository = MarketDataRepository(self.db_path)
        repository.replace_housing_points(
            "second_hand_housing",
            [
                {
                    "period_end": "2026-01-01",
                    "period_label": "2026-01",
                    "city": "北京",
                    "metric": "yoy",
                    "value": 10.0,
                    "unit": "%",
                    "frequency": "monthly",
                    "provider_key": "unit_test",
                    "source_url": "https://example.com",
                    "released_at": "",
                },
                {
                    "period_end": "2026-01-01",
                    "period_label": "2026-01",
                    "city": "北京",
                    "metric": "mom",
                    "value": 1.0,
                    "unit": "%",
                    "frequency": "monthly",
                    "provider_key": "unit_test",
                    "source_url": "https://example.com",
                    "released_at": "",
                },
                {
                    "period_end": "2026-01-01",
                    "period_label": "2026-01",
                    "city": "北京",
                    "metric": "global_index",
                    "value": 101.0,
                    "unit": "指数",
                    "frequency": "monthly",
                    "provider_key": "unit_test",
                    "source_url": "https://example.com",
                    "released_at": "",
                },
            ],
            status="live",
            warning_message="",
        )
        service = MarketDataService(repository=repository)

        payload = service.build_chart_payload(
            "second_hand_housing",
            range_type="custom",
            start_date="2026-01-01",
            end_date="2026-12-31",
            frequency="monthly",
            cities=["北京"],
        )

        series_by_name = {series["name"]: series for series in payload["series"]}
        self.assertEqual(payload["chart_type"], "housing_multi_metric")
        self.assertIn("北京 同比", series_by_name)
        self.assertIn("北京 环比", series_by_name)
        self.assertIn("北京 全局走势", series_by_name)
        self.assertEqual(series_by_name["北京 同比"]["points"][0]["value"], 10.0)
        self.assertEqual(series_by_name["北京 全局走势"]["points"][0]["unit"], "指数")


class MarketIndexVolumeTests(unittest.TestCase):
    """校验市场指数成交量会进入日报图表数据链路。"""

    def setUp(self) -> None:
        self.db_path = Path(".tmp-events-tests") / "market-index" / f"{self.id().split('.')[-1]}.db"
        if self.db_path.exists():
            self.db_path.unlink()

    def test_live_provider_extracts_daily_volume_from_index_frame(self) -> None:
        """校验 AKShare 日线表中的成交量会被解析为数值字段。"""
        frame = pd.DataFrame(
            [
                {"日期": "2026-03-24", "收盘": 3810.0, "成交量": "1,234,500"},
                {"日期": "2026-03-25", "收盘": 3825.0, "成交量": 2234500},
            ]
        )

        records = AkshareMarketDataProvider()._extract_market_records(frame)

        self.assertEqual(records[0]["volume"], 1234500.0)
        self.assertEqual(records[1]["volume"], 2234500.0)

    def test_market_history_store_round_trips_daily_volume(self) -> None:
        """校验本地市场历史库会持久化并读取每日成交量。"""
        store = MarketHistoryStore(self.db_path)

        store.upsert_symbol_history(
            symbol="CSI300",
            display_name="沪深300",
            currency="CNY",
            provider_key="unit-test",
            source_url="https://example.com",
            points=[
                type("Point", (), {"trade_date": pd.Timestamp("2026-03-24").date(), "close_price": 3810.0, "volume": 1000.0})(),
                type("Point", (), {"trade_date": pd.Timestamp("2026-03-25").date(), "close_price": 3825.0, "volume": 2000.0})(),
            ],
            status="live",
            window_label="近3个月",
            warning_message="",
        )

        points = store.load_points(symbol="CSI300", end_date=pd.Timestamp("2026-03-25").date(), window_days=10)

        self.assertEqual([point.volume for point in points], [1000.0, 2000.0])


if __name__ == "__main__":
    unittest.main()
