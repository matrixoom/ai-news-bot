import unittest
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from src.domain.external_data import MarketIndexHistoryPoint, MarketIndexSnapshot
from src.domain.market_monitoring import TrackedIndexDefinition
from src.providers.contracts import ProviderAvailability, ProviderStatus
from src.providers.live_data import AkshareMarketDataProvider
from src.services.market_history_store import MarketHistoryStore
from src.services.market_monitoring_service import MarketMonitoringService
from src.services.market_data_repository import MarketDataRepository
from src.services.market_data_service import MarketDataService
from src.services.market_data_sync_service import (
    MarketDataSyncService,
    _global_futures_points,
    _housing_points_from_frame,
    _load_brent_rows,
    _load_copper_rows,
    _load_gold_rows,
    _load_silver_rows,
)
from src.services.stock_market_repository import StockMarketRepository
from src.services.stock_market_sharding import (
    initialize_all_market_stock_shards,
    initialize_market_stock_shard,
    migrate_legacy_market_stock_shards,
    resolve_market_stock_shard_name,
    resolve_market_stock_shard_path,
)
from src.services.stock_market_service import StockMarketService
from src.services.stock_market_sync_service import StockMarketSyncService, _ak_etf_daily


class StockMarketShardingTests(unittest.TestCase):
    """校验股票日线分片路由与预建库结构。"""

    def setUp(self) -> None:
        """创建独立临时目录，避免固定分片文件名互相污染。"""

        self.temp_dir = TemporaryDirectory()
        self.shard_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        """清理本用例创建的临时分片库。"""

        self.temp_dir.cleanup()

    def test_stock_shard_router_uses_exchange_specific_code_positions(self) -> None:
        """校验沪深取第 4、5 位，北交所取最后一位。"""

        self.assertEqual(resolve_market_stock_shard_name("600519.SH"), "market_stock_SH_51.db")
        self.assertEqual(resolve_market_stock_shard_name("000010.SZ"), "market_stock_SZ_01.db")
        self.assertEqual(resolve_market_stock_shard_name("920118.BJ"), "market_stock_BJ_8.db")
        self.assertEqual(
            resolve_market_stock_shard_path("600519.SH", self.shard_dir),
            self.shard_dir / "SH" / "market_stock_SH_51.db",
        )
        self.assertEqual(
            resolve_market_stock_shard_path("000010.SZ", self.shard_dir),
            self.shard_dir / "SZ" / "market_stock_SZ_01.db",
        )
        self.assertEqual(
            resolve_market_stock_shard_path("920118.BJ", self.shard_dir),
            self.shard_dir / "BJ" / "market_stock_BJ_8.db",
        )

    def test_stock_shard_router_rejects_invalid_symbols(self) -> None:
        """校验非法代码格式和未知交易所会快速失败。"""

        invalid_symbols = ("", "600519", "60051.SH", "ABC519.SH", "600519.HK", "600519.sh")

        for symbol in invalid_symbols:
            with self.subTest(symbol=symbol), self.assertRaises(ValueError):
                resolve_market_stock_shard_name(symbol)

    def test_stock_shard_initializer_precreates_all_210_databases(self) -> None:
        """校验全部预分库均已创建统一日线表和查询索引。"""

        shard_paths = initialize_all_market_stock_shards(self.shard_dir)

        self.assertEqual(len(shard_paths), 210)
        self.assertTrue((self.shard_dir / "SH" / "market_stock_SH_00.db").exists())
        self.assertTrue((self.shard_dir / "SH" / "market_stock_SH_99.db").exists())
        self.assertTrue((self.shard_dir / "SZ" / "market_stock_SZ_00.db").exists())
        self.assertTrue((self.shard_dir / "SZ" / "market_stock_SZ_99.db").exists())
        self.assertTrue((self.shard_dir / "BJ" / "market_stock_BJ_0.db").exists())
        self.assertTrue((self.shard_dir / "BJ" / "market_stock_BJ_9.db").exists())
        with closing(sqlite3.connect(self.shard_dir / "SH" / "market_stock_SH_51.db")) as connection:
            table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'market_stock_daily_bar'"
            ).fetchone()
            index = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' "
                "AND name = 'idx_market_stock_daily_bar_symbol_date'"
            ).fetchone()

        self.assertIsNotNone(table)
        self.assertIsNotNone(index)

    def test_legacy_flat_shards_move_into_exchange_directories(self) -> None:
        """校验旧扁平分片会移动到交易所目录且数据保持不变。"""

        legacy_path = initialize_market_stock_shard(self.shard_dir / "market_stock_SZ_00.db")
        with closing(sqlite3.connect(legacy_path)) as connection:
            connection.execute(
                """
                INSERT INTO market_stock_daily_bar (
                    symbol, trade_date, open_price, close_price, high_price, low_price,
                    volume, provider_key, source_url, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("000001.SZ", "2026-06-05", 10, 11, 12, 9, 100, "unit-test", "", "2026-06-06T00:00:00Z"),
            )
            connection.commit()

        moved_paths = migrate_legacy_market_stock_shards(self.shard_dir, self.shard_dir)
        target_path = self.shard_dir / "SZ" / "market_stock_SZ_00.db"

        self.assertEqual(moved_paths, [target_path])
        self.assertFalse(legacy_path.exists())
        with closing(sqlite3.connect(target_path)) as connection:
            close_price = connection.execute(
                "SELECT close_price FROM market_stock_daily_bar WHERE symbol = ?",
                ("000001.SZ",),
            ).fetchone()[0]
        self.assertEqual(close_price, 11)

    def test_legacy_empty_placeholder_is_ignored_when_target_exists(self) -> None:
        """校验工具创建的旧路径空文件不会阻断已完成的目录迁移。"""

        legacy_path = self.shard_dir / "market_stock_SH_49.db"
        legacy_path.touch()
        target_path = initialize_market_stock_shard(
            self.shard_dir / "SH" / "market_stock_SH_49.db"
        )

        moved_paths = migrate_legacy_market_stock_shards(self.shard_dir, self.shard_dir)

        self.assertEqual(moved_paths, [])
        self.assertEqual(legacy_path.stat().st_size, 0)
        self.assertTrue(target_path.exists())


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


class StockMarketModuleTests(unittest.TestCase):
    """校验股票市场标的、日线与懒加载链路。"""

    def setUp(self) -> None:
        """创建主库和分片库共用的独立临时目录。"""

        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "market_data.db"

    def tearDown(self) -> None:
        """清理本用例创建的主库和分片库。"""

        self.temp_dir.cleanup()

    def _repository(self) -> StockMarketRepository:
        """创建不批量预建分片的测试仓储，仅按访问目标自愈建表。"""

        return StockMarketRepository(self.db_path, precreate_shards=False)

    def _create_legacy_daily_bar_table(self, rows: list[tuple[object, ...]]) -> None:
        """创建旧版主库日线表并写入待迁移记录。"""

        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                CREATE TABLE market_stock_daily_bar (
                    symbol TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    open_price REAL NOT NULL,
                    close_price REAL NOT NULL,
                    high_price REAL NOT NULL,
                    low_price REAL NOT NULL,
                    volume REAL NOT NULL,
                    ma5 REAL,
                    ma10 REAL,
                    ma20 REAL,
                    ma60 REAL,
                    ma120 REAL,
                    provider_key TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    PRIMARY KEY(symbol, trade_date)
                )
                """
            )
            connection.executemany(
                """
                INSERT INTO market_stock_daily_bar (
                    symbol, trade_date, open_price, close_price, high_price, low_price,
                    volume, ma5, ma10, ma20, ma60, ma120, provider_key, source_url, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            connection.commit()

    def test_stock_universe_sync_persists_a_share_and_etf_symbols(self) -> None:
        """校验 A 股与 ETF 标的统一持久化，并可按名称或代码搜索。"""
        repository = self._repository()
        syncer = StockMarketSyncService(
            repository=repository,
            stock_universe_loader=lambda: pd.DataFrame(
                [
                    {"code": "000001", "name": "平安银行"},
                    {"code": "688111", "name": "金山办公"},
                ]
            ),
            etf_universe_loader=lambda: pd.DataFrame([{"代码": "159915", "名称": "创业板ETF"}]),
        )

        result = syncer.sync_universe()
        items, total = repository.search_instruments(query="平安", limit=10, offset=0)

        self.assertEqual(result["total"], 3)
        self.assertEqual(total, 1)
        self.assertEqual(items[0].symbol, "000001.SZ")
        self.assertEqual(repository.get_instrument("688111.SH").market_board, "科创板")
        self.assertEqual(repository.get_instrument("159915.SZ").instrument_type, "etf")

    def test_stock_universe_sync_keeps_stock_rows_when_etf_source_fails(self) -> None:
        """校验 ETF 上游失败不会拖垮 A 股标的入库。"""
        repository = self._repository()
        syncer = StockMarketSyncService(
            repository=repository,
            stock_universe_loader=lambda: pd.DataFrame([{"code": "000001", "name": "平安银行"}]),
            etf_universe_loader=Mock(side_effect=RuntimeError("ETF proxy unavailable")),
        )

        result = syncer.sync_universe()
        items, total = repository.search_instruments(query="000001", limit=10, offset=0)

        self.assertEqual(result["stock"], 1)
        self.assertEqual(result["etf"], 0)
        self.assertEqual(total, 1)
        self.assertEqual(items[0].symbol, "000001.SZ")
        self.assertIn("ETF", result["warnings"][0])

    def test_daily_bar_upsert_is_idempotent_and_keeps_latest_values(self) -> None:
        """校验同一交易日重复写入只更新一行，不产生重复行情。"""
        repository = self._repository()
        repository.upsert_instruments(
            [
                {
                    "symbol": "000001.SZ",
                    "code": "000001",
                    "exchange": "SZ",
                    "name": "平安银行",
                    "instrument_type": "stock",
                    "market_board": "深市主板",
                    "listing_status": "listed",
                }
            ]
        )

        repository.upsert_daily_bars(
            "000001.SZ",
            [
                {
                    "trade_date": "2026-05-29",
                    "open_price": 10,
                    "close_price": 11,
                    "high_price": 12,
                    "low_price": 9,
                    "volume": 100,
                    "ma5": None,
                    "ma10": None,
                    "ma20": None,
                    "ma60": None,
                    "ma120": None,
                }
            ],
        )
        repository.upsert_daily_bars(
            "000001.SZ",
            [
                {
                    "trade_date": "2026-05-29",
                    "open_price": 10,
                    "close_price": 12.5,
                    "high_price": 13,
                    "low_price": 9.5,
                    "volume": 200,
                    "ma5": 12.5,
                    "ma10": None,
                    "ma20": None,
                    "ma60": None,
                    "ma120": None,
                }
            ],
        )

        points = repository.load_daily_bars(symbol="000001.SZ", start_date="2026-05-01", end_date="2026-06-30")

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].close_price, 12.5)
        self.assertEqual(points[0].volume, 200)
        self.assertEqual(repository.get_sync_state("000001.SZ").daily_point_count, 1)
        self.assertTrue((self.db_path.parent / "market" / "SZ" / "market_stock_SZ_00.db").exists())
        with closing(sqlite3.connect(self.db_path)) as connection:
            legacy_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'market_stock_daily_bar'"
            ).fetchone()
        self.assertIsNone(legacy_table)

    def test_legacy_stock_daily_bars_migrate_to_shards_and_remove_main_table(self) -> None:
        """校验旧表数据按规则迁移，校验成功后才从主库移除。"""

        self._create_legacy_daily_bar_table(
            [
                (
                    "600519.SH",
                    "2026-06-05",
                    1500,
                    1510,
                    1520,
                    1490,
                    100,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "unit-test",
                    "https://example.com/sh",
                    "2026-06-06T00:00:00Z",
                ),
                (
                    "920118.BJ",
                    "2026-06-05",
                    20,
                    21,
                    22,
                    19,
                    200,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "unit-test",
                    "https://example.com/bj",
                    "2026-06-06T00:00:00Z",
                ),
            ]
        )

        repository = self._repository()
        repository_again = self._repository()

        self.assertEqual(
            repository.load_daily_bars(symbol="600519.SH", start_date="2026-06-01", end_date="2026-06-30")[0].close_price,
            1510,
        )
        self.assertEqual(
            repository_again.load_daily_bars(symbol="920118.BJ", start_date="2026-06-01", end_date="2026-06-30")[0].volume,
            200,
        )
        with closing(sqlite3.connect(self.db_path)) as connection:
            legacy_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'market_stock_daily_bar'"
            ).fetchone()
        with closing(sqlite3.connect(self.db_path.parent / "market" / "SH" / "market_stock_SH_51.db")) as connection:
            sh_count = connection.execute("SELECT COUNT(*) FROM market_stock_daily_bar").fetchone()[0]
        with closing(sqlite3.connect(self.db_path.parent / "market" / "BJ" / "market_stock_BJ_8.db")) as connection:
            bj_count = connection.execute("SELECT COUNT(*) FROM market_stock_daily_bar").fetchone()[0]

        self.assertIsNone(legacy_table)
        self.assertEqual(sh_count, 1)
        self.assertEqual(bj_count, 1)

    def test_legacy_stock_daily_bar_migration_keeps_source_on_invalid_symbol(self) -> None:
        """校验旧表存在非法 symbol 时迁移失败且源表完整保留。"""

        self._create_legacy_daily_bar_table(
            [
                (
                    "600519.HK",
                    "2026-06-05",
                    1500,
                    1510,
                    1520,
                    1490,
                    100,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "unit-test",
                    "https://example.com/hk",
                    "2026-06-06T00:00:00Z",
                )
            ]
        )

        with self.assertRaisesRegex(ValueError, "HK"):
            self._repository()

        with closing(sqlite3.connect(self.db_path)) as connection:
            source_count = connection.execute("SELECT COUNT(*) FROM market_stock_daily_bar").fetchone()[0]
        self.assertEqual(source_count, 1)

    def test_stock_search_loads_latest_prices_from_multiple_shards(self) -> None:
        """校验股票列表按分片批量补充最新收盘价。"""

        repository = self._repository()
        instruments = [
            ("600519.SH", "600519", "SH", "贵州茅台"),
            ("000010.SZ", "000010", "SZ", "美丽生态"),
            ("920118.BJ", "920118", "BJ", "太湖远大"),
            ("000011.SZ", "000011", "SZ", "深物业A"),
        ]
        repository.upsert_instruments(
            [
                {
                    "symbol": symbol,
                    "code": code,
                    "exchange": exchange,
                    "name": name,
                    "instrument_type": "stock",
                    "market_board": "测试板块",
                    "listing_status": "listed",
                }
                for symbol, code, exchange, name in instruments
            ]
        )
        for symbol, close_price in (("600519.SH", 1510), ("000010.SZ", 4.8), ("920118.BJ", 21)):
            repository.upsert_daily_bars(
                symbol,
                [
                    {
                        "trade_date": "2026-06-05",
                        "open_price": close_price - 1,
                        "close_price": close_price,
                        "high_price": close_price + 1,
                        "low_price": close_price - 2,
                        "volume": 100,
                    }
                ],
            )

        items, total = repository.search_instruments(limit=10, offset=0)
        prices = {item.symbol: item.latest_price for item in items}

        self.assertEqual(total, 4)
        self.assertEqual(prices["600519.SH"], 1510)
        self.assertEqual(prices["000010.SZ"], 4.8)
        self.assertEqual(prices["920118.BJ"], 21)
        self.assertIsNone(prices["000011.SZ"])

    def test_stock_search_repairs_existing_empty_shard_database(self) -> None:
        """校验读路径会修复已存在但缺少 schema 的分片文件。"""

        empty_shard_path = self.db_path.parent / "market" / "SH" / "market_stock_SH_51.db"
        empty_shard_path.parent.mkdir(parents=True, exist_ok=True)
        empty_shard_path.touch()
        repository = self._repository()
        repository.upsert_instruments(
            [
                {
                    "symbol": "600519.SH",
                    "code": "600519",
                    "exchange": "SH",
                    "name": "贵州茅台",
                    "instrument_type": "stock",
                    "market_board": "沪市主板",
                    "listing_status": "listed",
                }
            ]
        )

        items, total = repository.search_instruments(limit=10, offset=0)

        self.assertEqual(total, 1)
        self.assertIsNone(items[0].latest_price)
        with closing(sqlite3.connect(empty_shard_path)) as connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'market_stock_daily_bar'"
            ).fetchone()
        self.assertIsNotNone(table)

    def test_stock_detail_lazy_loads_three_month_window_when_history_absent(self) -> None:
        """校验首次查看股票详情时，会懒加载日线并返回概况和财报数据。"""
        repository = self._repository()
        repository.upsert_instruments(
            [
                {
                    "symbol": "000001.SZ",
                    "code": "000001",
                    "exchange": "SZ",
                    "name": "平安银行",
                    "instrument_type": "stock",
                    "market_board": "深市主板",
                    "listing_status": "listed",
                }
            ]
        )
        daily_frame = pd.DataFrame(
            [
                {"日期": f"2026-03-{day:02d}", "开盘": 10 + day, "收盘": 11 + day, "最高": 12 + day, "最低": 9 + day, "成交量": 1000 + day}
                for day in range(1, 8)
            ]
        )
        profile_frame = pd.DataFrame(
            [
                {"item": "公司名称", "value": "平安银行股份有限公司"},
                {"item": "行业", "value": "银行"},
                {"item": "地区", "value": "深圳"},
                {"item": "上市时间", "value": "19910403"},
            ]
        )
        benefit_frame = pd.DataFrame(
            [
                {"报告期": "2026-03-31", "*营业总收入": "352.77亿", "*营业支出": "178.88亿"},
                {"报告期": "2025-12-31", "*营业总收入": "1314.42亿", "*营业支出": "800.34亿"},
            ]
        )
        cash_frame = pd.DataFrame(
            [
                {"报告期": "2026-03-31", "*经营活动产生的现金流量净额": "378.02亿"},
                {"报告期": "2025-12-31", "*经营活动产生的现金流量净额": "3158.58亿"},
            ]
        )
        debt_frame = pd.DataFrame(
            [
                {"报告期": "2026-03-31", "*负债合计": "5.49万亿", "*资产合计": "6.03万亿"},
                {"报告期": "2025-12-31", "*负债合计": "5.37万亿", "*资产合计": "5.93万亿"},
            ]
        )
        syncer = StockMarketSyncService(
            repository=repository,
            stock_daily_loader=lambda **_: daily_frame,
            profile_loader=lambda **_: profile_frame,
            benefit_loader=lambda **_: benefit_frame,
            cash_loader=lambda **_: cash_frame,
            debt_loader=lambda **_: debt_frame,
        )
        service = StockMarketService(repository=repository, sync_service=syncer)

        payload = service.build_stock_detail_payload(
            "000001.SZ",
            range_type="custom",
            start_date="2026-03-01",
            end_date="2026-03-31",
            financial_report_type="quarterly",
        )

        self.assertEqual(payload["instrument"]["name"], "平安银行")
        self.assertEqual(len(payload["daily_bars"]), 7)
        self.assertEqual(payload["daily_bars"][4]["ma5"], 14.0)
        self.assertEqual(payload["profile"]["industry"], "银行")
        revenue_series = next(series for series in payload["financials"]["series"] if series["metric"] == "revenue")
        self.assertEqual(revenue_series["points"][0]["value"], 352.77)

    def test_stock_detail_logs_compact_warning_when_lazy_daily_sync_fails(self) -> None:
        """校验日线懒加载失败时只记录短 warning，不输出完整异常栈。"""
        repository = self._repository()
        repository.upsert_instruments(
            [
                {
                    "symbol": "159007.SZ",
                    "code": "159007",
                    "exchange": "SZ",
                    "name": "华泰柏瑞中证畜牧养殖",
                    "instrument_type": "etf",
                    "market_board": "ETF",
                    "listing_status": "listed",
                }
            ]
        )
        syncer = StockMarketSyncService(
            repository=repository,
            etf_daily_loader=Mock(side_effect=RuntimeError("ProxyError: Unable to connect to proxy")),
        )
        service = StockMarketService(repository=repository, sync_service=syncer)

        with patch("src.services.stock_market_service.logger.exception") as exception_logger:
            payload = service.build_stock_detail_payload("159007.SZ")

        exception_logger.assert_not_called()
        self.assertIn("代理连接失败", payload["sync_state"]["warning_message"])

    def test_etf_daily_loader_falls_back_to_sina_history(self) -> None:
        """校验 ETF 东方财富日线失败时回退新浪历史日线。"""
        fake_akshare = SimpleNamespace(
            fund_etf_hist_em=Mock(side_effect=RuntimeError("ProxyError: Unable to connect to proxy")),
            fund_etf_hist_sina=Mock(
                return_value=pd.DataFrame(
                    [
                        {"date": "2026-03-01", "open": 1.0, "close": 1.1, "high": 1.2, "low": 0.9, "volume": 1000},
                        {"date": "2026-06-01", "open": 2.0, "close": 2.1, "high": 2.2, "low": 1.9, "volume": 2000},
                    ]
                )
            ),
        )

        with patch.dict("sys.modules", {"akshare": fake_akshare}):
            frame = _ak_etf_daily(symbol="159007", start_date="20260501", end_date="20260606")

        self.assertEqual(frame.to_dict("records"), [{"date": "2026-06-01", "open": 2.0, "close": 2.1, "high": 2.2, "low": 1.9, "volume": 2000}])
        fake_akshare.fund_etf_hist_sina.assert_called_once_with(symbol="sz159007")


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

    def test_cn_index_history_prefers_stable_sina_endpoint(self) -> None:
        """校验国内宽基指数优先使用稳定的新浪日线，避免主刷新被慢端点阻塞。"""
        frame = pd.DataFrame([{"date": "2026-05-29", "close": 3825.0, "volume": 2234500}])
        fake_akshare = SimpleNamespace(
            stock_zh_index_daily=Mock(return_value=frame),
            stock_zh_index_daily_em=Mock(side_effect=RuntimeError("eastmoney should remain fallback only")),
        )

        result = AkshareMarketDataProvider()._load_market_frame(
            akshare=fake_akshare,
            symbol="CSI300",
            trade_date=date(2026, 5, 29),
        )

        self.assertIs(result, frame)
        fake_akshare.stock_zh_index_daily.assert_called_once()
        self.assertEqual(fake_akshare.stock_zh_index_daily.call_args.kwargs["symbol"], "sh000300")
        fake_akshare.stock_zh_index_daily_em.assert_not_called()

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

    def test_market_history_store_keeps_existing_rows_when_upserting_selected_window(self) -> None:
        """校验刷新选中范围时只更新同日期点，不删除范围内外已有历史。"""
        store = MarketHistoryStore(self.db_path)
        seed_points = [
            MarketIndexHistoryPoint(date(2024, 1, 1), 3600.0),
            MarketIndexHistoryPoint(date(2026, 3, 20), 3900.0),
            MarketIndexHistoryPoint(date(2026, 3, 23), 3910.0),
        ]
        store.upsert_symbol_history(
            symbol="CSI300",
            display_name="沪深300",
            currency="CNY",
            provider_key="unit-test",
            source_url="https://example.com",
            points=seed_points,
            status="live",
            window_label="近6个月",
            warning_message="",
        )

        store.upsert_symbol_history(
            symbol="CSI300",
            display_name="沪深300",
            currency="CNY",
            provider_key="unit-test",
            source_url="https://example.com",
            points=[MarketIndexHistoryPoint(date(2026, 3, 23), 3950.0)],
            status="live",
            window_label="近3个月",
            warning_message="",
        )

        points = store.load_points(symbol="CSI300", end_date=date(2026, 3, 31), window_days=1096)

        self.assertEqual(
            [(point.trade_date, point.close_price) for point in points],
            [
                (date(2024, 1, 1), 3600.0),
                (date(2026, 3, 20), 3900.0),
                (date(2026, 3, 23), 3950.0),
            ],
        )

    def test_market_refresh_uses_selected_window_and_reports_symbol_progress(self) -> None:
        """校验专用全量刷新逐指数汇报进度，并保留本地已有历史。"""

        class RecordingProvider:
            """返回一条完整历史帧，模拟宽基指数实时数据源。"""

            provider_key = "unit-test"

            def __init__(self):
                self.requested_windows = []

            def healthcheck(self) -> ProviderStatus:
                """返回可用状态。"""
                return ProviderStatus("unit-test", ProviderAvailability.LIVE, "", "2026-05-29T08:00:00Z")

            def fetch_index_snapshots(self, *, symbols, trade_date, history_window_days=180):
                """记录窗口并为请求指数返回完整历史帧。"""
                self.requested_windows.append(history_window_days)
                points = tuple(
                    MarketIndexHistoryPoint(date(2026, 1, 1) + pd.Timedelta(days=offset), 4000.0 + offset)
                    for offset in range(149)
                )
                return [
                    MarketIndexSnapshot(
                        provider="unit-test",
                        symbol=symbols[0],
                        display_name="沪深300",
                        trade_date=trade_date,
                        close_price=4148.0,
                        currency="CNY",
                        source_url="https://example.com",
                        history_points=points,
                    )
                ]

        store = MarketHistoryStore(self.db_path)
        store.upsert_symbol_history(
            symbol="CSI300",
            display_name="沪深300",
            currency="CNY",
            provider_key="unit-test",
            source_url="https://example.com",
            points=[MarketIndexHistoryPoint(date(2025, 12, 15), 9999.0)],
            status="live",
            window_label="近6个月",
            warning_message="",
        )
        progress_events = []
        provider = RecordingProvider()
        service = MarketMonitoringService(
            market_provider=provider,
            store=store,
            registry={"CSI300": TrackedIndexDefinition("CSI300", "沪深300", "unit-test", "CNY")},
        )

        service.refresh_store(
            symbols=["CSI300"],
            trade_date=date(2026, 5, 29),
            history_window_days=731,
            progress_callback=progress_events.append,
        )

        points = store.load_points(symbol="CSI300", end_date=date(2026, 5, 29), window_days=180)
        self.assertEqual(provider.requested_windows, [731])
        self.assertIn(9999.0, [point.close_price for point in points])
        self.assertEqual(progress_events[-1]["status"], "completed")
        self.assertEqual(progress_events[-1]["completed"], 1)
        self.assertEqual(progress_events[-1]["total"], 1)

    def test_market_refresh_keeps_existing_window_when_provider_history_is_too_short(self) -> None:
        """校验上游短序列不会清空本地仍可展示的三个月历史。"""

        class ShortHistoryProvider:
            """返回不足一个月的短序列，模拟上游降级响应。"""

            provider_key = "unit-test"

            def healthcheck(self) -> ProviderStatus:
                """返回可用状态，让用例聚焦历史完整性校验。"""
                return ProviderStatus("unit-test", ProviderAvailability.LIVE, "", "2026-05-29T08:00:00Z")

            def fetch_index_snapshots(self, *, symbols, trade_date, history_window_days=180):
                """仅返回五个日线点。"""
                _ = history_window_days
                points = tuple(
                    MarketIndexHistoryPoint(date(2026, 5, 25) + pd.Timedelta(days=offset), 4100.0 + offset)
                    for offset in range(5)
                )
                return [
                    MarketIndexSnapshot(
                        provider="unit-test",
                        symbol=symbols[0],
                        display_name="沪深300",
                        trade_date=trade_date,
                        close_price=4104.0,
                        currency="CNY",
                        source_url="https://example.com",
                        history_points=points,
                    )
                ]

        store = MarketHistoryStore(self.db_path)
        store.upsert_symbol_history(
            symbol="CSI300",
            display_name="沪深300",
            currency="CNY",
            provider_key="unit-test",
            source_url="https://example.com",
            points=[MarketIndexHistoryPoint(date(2026, 3, 15), 3999.0)],
            status="live",
            window_label="近3个月",
            warning_message="",
        )
        progress_events = []
        service = MarketMonitoringService(
            market_provider=ShortHistoryProvider(),
            store=store,
            registry={"CSI300": TrackedIndexDefinition("CSI300", "沪深300", "unit-test", "CNY")},
        )

        service.refresh_store(
            symbols=["CSI300"],
            trade_date=date(2026, 5, 29),
            history_window_days=180,
            progress_callback=progress_events.append,
        )

        points = store.load_points(symbol="CSI300", end_date=date(2026, 5, 29), window_days=180)
        self.assertEqual(
            [(point.trade_date, point.close_price) for point in points],
            [
                (date(2026, 3, 15), 3999.0),
                (date(2026, 5, 25), 4100.0),
                (date(2026, 5, 26), 4101.0),
                (date(2026, 5, 27), 4102.0),
                (date(2026, 5, 28), 4103.0),
                (date(2026, 5, 29), 4104.0),
            ],
        )
        self.assertEqual(progress_events[-1]["status"], "completed")


class MarketDataSyncTests(unittest.TestCase):
    """校验 Market Data 外部历史行情的解析、回退和单图刷新隔离。"""

    def setUp(self) -> None:
        self.db_path = Path(".tmp-events-tests") / "market-data-sync" / f"{self.id().split('.')[-1]}.db"
        if self.db_path.exists():
            self.db_path.unlink()

    def test_global_futures_parser_reads_close_column_instead_of_high_column(self) -> None:
        """校验全球期货解析使用收盘列，避免把日内最高价画成历史收盘趋势。"""
        frame = pd.DataFrame(
            [
                {
                    "日期": "2026-05-29",
                    "开盘": 88.53,
                    "收盘": 87.78,
                    "最高": 89.02,
                    "最低": 86.35,
                }
            ]
        )

        points = _global_futures_points(frame, "美元/桶", "unit-test")

        self.assertEqual(points[0]["value"], 87.78)

    def test_global_futures_loaders_fall_back_to_sina_history(self) -> None:
        """校验东方财富历史端点失败时，布伦特和贵金属改用新浪日线继续刷新。"""
        frames = {
            "OIL": pd.DataFrame([{"date": "2026-05-29", "close": 91.1}]),
            "XAU": pd.DataFrame([{"date": "2026-05-29", "close": 4539.78}]),
            "XAG": pd.DataFrame([{"date": "2026-05-29", "close": 75.274}]),
            "CAD": pd.DataFrame([{"date": "2026-05-29", "close": 13606.0}]),
        }
        fake_akshare = SimpleNamespace(
            futures_global_hist_em=Mock(side_effect=RuntimeError("eastmoney unavailable")),
            futures_foreign_hist=Mock(side_effect=lambda symbol: frames[symbol]),
        )

        with (
            patch.dict("sys.modules", {"akshare": fake_akshare}),
            patch("src.services.market_data_sync_service._world_bank_commodity_points", return_value=[]),
        ):
            brent_points = _load_brent_rows()
            gold_points = _load_gold_rows()
            silver_points = _load_silver_rows()
            copper_points = _load_copper_rows()

        self.assertEqual(brent_points[-1]["value"], 91.1)
        self.assertEqual(gold_points[-1]["value"], 4539.78)
        self.assertEqual(silver_points[-1]["value"], 75.274)
        self.assertAlmostEqual(copper_points[-1]["value"], 13606.0 / 2204.6226218488)
        self.assertEqual(
            [call.kwargs["symbol"] for call in fake_akshare.futures_foreign_hist.call_args_list],
            ["OIL", "XAU", "XAG", "CAD"],
        )

    def test_global_futures_loader_falls_back_when_eastmoney_returns_empty_frame(self) -> None:
        """校验东方财富返回空表时仍会切换新浪，不把空结果继续传给仓储。"""
        fake_akshare = SimpleNamespace(
            futures_global_hist_em=Mock(return_value=pd.DataFrame()),
            futures_foreign_hist=Mock(
                return_value=pd.DataFrame([{"date": "2026-05-29", "close": 91.1}])
            ),
        )

        with patch.dict("sys.modules", {"akshare": fake_akshare}):
            points = _load_brent_rows()

        self.assertEqual(points[-1]["value"], 91.1)
        fake_akshare.futures_foreign_hist.assert_called_once_with(symbol="OIL")

    def test_single_chart_refresh_does_not_load_sibling_indicator(self) -> None:
        """校验点击单图刷新时，不会被同分类其他上游的失败拖累。"""
        repository = MarketDataRepository(self.db_path)
        wti_points = [
            {
                "period_end": "2026-05-29",
                "period_label": "2026-05-29",
                "value": 87.78,
                "unit": "美元/桶",
                "frequency": "daily",
                "provider_key": "unit-test",
                "source_url": "https://example.com",
                "released_at": "",
            }
        ]
        service = MarketDataSyncService(
            repository=repository,
            wti_loader=lambda: wti_points,
            brent_loader=Mock(side_effect=RuntimeError("brent unavailable")),
        )

        result = service.sync_indicator_history("wti_crude_oil")

        self.assertEqual(result, {"wti_crude_oil": 1})
        self.assertEqual(
            repository.load_points(
                indicator_id="wti_crude_oil",
                start_date="2026-05-29",
                end_date="2026-05-29",
                frequency="daily",
            )[0].value,
            87.78,
        )

    def test_market_data_service_routes_refresh_to_selected_indicator_only(self) -> None:
        """校验前端单图刷新接口只同步当前图表对应的指标。"""
        repository = MarketDataRepository(self.db_path)
        service = MarketDataService(repository=repository)

        with patch(
            "src.services.market_data_sync_service.MarketDataSyncService.sync_indicator_history",
            return_value={"wti_crude_oil": 1},
        ) as sync_indicator:
            result = service.sync_chart("wti_crude_oil")

        self.assertEqual(result, {"ok": True, "point_counts": {"wti_crude_oil": 1}})
        sync_indicator.assert_called_once_with("wti_crude_oil")

    def test_empty_housing_refresh_keeps_existing_history(self) -> None:
        """校验房地产上游全空时快速失败，不会删除库内仍可展示的历史序列。"""
        repository = MarketDataRepository(self.db_path)
        cities_before_refresh = repository.list_housing_cities("second_hand_housing")
        service = MarketDataSyncService(repository=repository, housing_loader=lambda: [])

        with self.assertRaisesRegex(ValueError, "second_hand_housing"):
            service.sync_indicator_history("second_hand_housing")

        self.assertEqual(repository.list_housing_cities("second_hand_housing"), cities_before_refresh)


class MarketIndexSessionBoundaryTests(unittest.TestCase):
    """校验宽基指数仅在有效交易日拼接盘中报价。"""

    def test_weekend_does_not_append_spot_session_quote(self) -> None:
        """校验周末即使时间晚于收盘时刻，也不会错误尝试补入盘中报价。"""

        class WeekendDateTime(datetime):
            """固定当前时间到周日下午，复现周末刷新边界。"""

            @classmethod
            def now(cls, tz=None):
                """返回固定 UTC 时间，供服务转换到上海时区。"""
                return cls(2026, 5, 31, 8, 0, tzinfo=UTC)

        with patch("src.providers.live_data.datetime", WeekendDateTime):
            should_append = AkshareMarketDataProvider()._should_use_spot_session_close_for_trade_date(
                market="cn",
                trade_date=date(2026, 5, 31),
            )

        self.assertFalse(should_append)


if __name__ == "__main__":
    unittest.main()
