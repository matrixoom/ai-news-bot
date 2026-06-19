"""A 股股票市场本地 SQLite 仓储。"""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any, Collection, Iterator, Mapping, Sequence

from src.services.stock_market_sharding import (
    initialize_all_market_stock_shards,
    initialize_market_stock_shard,
    iter_market_stock_shard_paths,
    migrate_legacy_market_stock_shards,
    resolve_market_stock_shard_path,
)


class StockMarketValidationError(ValueError):
    """股票市场参数校验失败。"""


@dataclass(frozen=True)
class StockInstrument:
    """A 股或 ETF 标的基础信息。"""

    symbol: str
    code: str
    exchange: str
    name: str
    instrument_type: str
    market_board: str
    listing_status: str
    updated_at: str
    latest_price: float | None = None


@dataclass(frozen=True)
class StockDailyBar:
    """单个交易日的 OHLCV 与均线数据。"""

    symbol: str
    trade_date: str
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    volume: float
    ma5: float | None
    ma10: float | None
    ma20: float | None
    ma60: float | None
    ma120: float | None
    pe_ttm: float | None
    pb_mrq: float | None
    dividend_yield_ttm: float | None
    total_market_cap: float | None


@dataclass(frozen=True)
class StockProfile:
    """股票公司概况、板块与属性信息。"""

    symbol: str
    company_name: str
    industry: str
    sector: str
    region: str
    listing_date: str
    attributes: list[str]
    summary: str
    updated_at: str


@dataclass(frozen=True)
class StockFinancialMetric:
    """单个报告期的一项财务指标。"""

    symbol: str
    report_period: str
    report_type: str
    metric: str
    label: str
    value: float
    unit: str


@dataclass(frozen=True)
class StockSyncState:
    """股票日线、概况和财报同步状态。"""

    symbol: str
    latest_trade_date: str | None
    earliest_trade_date: str | None
    daily_point_count: int
    profile_status: str
    financial_status: str
    warning_message: str
    synced_at: str


def _utc_now() -> str:
    """返回当前 UTC ISO 字符串。"""

    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _unavailable_market_breadth() -> dict[str, Any]:
    """返回市场宽度不可用时的稳定结构。"""

    return {
        "trade_date": None,
        "advanced": 0,
        "declined": 0,
        "unchanged": 0,
        "total": 0,
        "status": "unavailable",
    }


class StockMarketRepository:
    """管理股票市场相关表的读写。"""

    def __init__(
        self,
        db_path: str | Path = ".data/market_data.db",
        *,
        shard_dir: str | Path | None = None,
        precreate_shards: bool = True,
    ) -> None:
        """初始化仓储并确保表结构存在。

        Args:
            db_path: SQLite 数据库路径。
            shard_dir: 日线分片根目录，默认是主库同级的 `market/`。
            precreate_shards: 是否在初始化时预建全部 210 个分片。

        Returns:
            已完成建表的仓储实例。
        """

        self._db_path = Path(db_path)
        self._shard_dir = Path(shard_dir) if shard_dir is not None else self._db_path.parent / "market"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._shard_dir.mkdir(parents=True, exist_ok=True)
        self._precreate_shards = precreate_shards
        self._initialize()

    @property
    def db_path(self) -> Path:
        """返回当前仓储使用的数据库路径。"""

        return self._db_path

    def upsert_instruments(self, instruments: Sequence[Mapping[str, Any]]) -> int:
        """批量写入 A 股/ETF 标的基础信息。

        Args:
            instruments: 标准化后的标的信息。

        Returns:
            本次处理的标的数量。
        """

        timestamp = _utc_now()
        rows = [
            (
                str(item["symbol"]),
                str(item["code"]),
                str(item["exchange"]),
                str(item["name"]),
                str(item["instrument_type"]),
                str(item.get("market_board", "")),
                str(item.get("listing_status", "listed")),
                str(item.get("source_url", "")),
                timestamp,
                timestamp,
            )
            for item in instruments
        ]
        with self._session() as connection:
            connection.executemany(
                """
                INSERT INTO market_stock_instrument (
                    symbol, code, exchange, name, instrument_type, market_board,
                    listing_status, source_url, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    code=excluded.code,
                    exchange=excluded.exchange,
                    name=excluded.name,
                    instrument_type=excluded.instrument_type,
                    market_board=excluded.market_board,
                    listing_status=excluded.listing_status,
                    source_url=excluded.source_url,
                    updated_at=excluded.updated_at
                """,
                rows,
            )
        return len(rows)

    def count_instruments(self) -> int:
        """统计已持久化的股票/ETF 标的数量。"""

        with self._session() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM market_stock_instrument").fetchone()
        return int(row["count"]) if row else 0

    def load_market_breadth(self) -> dict[str, Any]:
        """聚合最近两个交易日的 A 股上涨、下跌和平盘家数。

        Returns:
            包含交易日、上涨数、下跌数、平盘数、有效总数和状态的字典。
        """

        with self._session() as connection:
            eligible_symbols = {
                str(row["symbol"])
                for row in connection.execute(
                    """
                    SELECT symbol
                    FROM market_stock_instrument
                    WHERE instrument_type = 'stock' AND listing_status = 'listed'
                    """
                ).fetchall()
            }
        if not eligible_symbols:
            return _unavailable_market_breadth()

        existing_shards = [path for path in iter_market_stock_shard_paths(self._shard_dir) if path.exists()]
        candidate_dates: set[str] = set()
        for shard_path in existing_shards:
            with self._shard_session(shard_path) as connection:
                rows = connection.execute(
                    """
                    SELECT DISTINCT trade_date
                    FROM market_stock_daily_bar
                    ORDER BY trade_date DESC
                    LIMIT 2
                    """
                ).fetchall()
            candidate_dates.update(str(row["trade_date"]) for row in rows)

        latest_dates = sorted(candidate_dates, reverse=True)[:2]
        if len(latest_dates) < 2:
            return _unavailable_market_breadth()
        latest_date, previous_date = latest_dates

        closes_by_symbol: dict[str, dict[str, float]] = defaultdict(dict)
        for shard_path in existing_shards:
            with self._shard_session(shard_path) as connection:
                rows = connection.execute(
                    """
                    SELECT symbol, trade_date, close_price
                    FROM market_stock_daily_bar
                    WHERE trade_date IN (?, ?)
                    """,
                    (previous_date, latest_date),
                ).fetchall()
            for row in rows:
                symbol = str(row["symbol"])
                if symbol in eligible_symbols:
                    closes_by_symbol[symbol][str(row["trade_date"])] = float(row["close_price"])

        advanced = declined = unchanged = 0
        for closes in closes_by_symbol.values():
            if latest_date not in closes or previous_date not in closes:
                continue
            change = closes[latest_date] - closes[previous_date]
            if change > 0:
                advanced += 1
            elif change < 0:
                declined += 1
            else:
                unchanged += 1
        total = advanced + declined + unchanged
        if total == 0:
            return _unavailable_market_breadth()
        return {
            "trade_date": latest_date,
            "advanced": advanced,
            "declined": declined,
            "unchanged": unchanged,
            "total": total,
            "status": "live",
        }

    def search_instruments(
        self,
        *,
        query: str = "",
        instrument_type: str = "all",
        market_board: str = "all",
        listing_status: str = "all",
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[StockInstrument], int]:
        """按代码、名称筛选股票/ETF 标的。

        Args:
            query: 股票代码或名称关键字。
            instrument_type: `stock`、`etf` 或 `all`。
            market_board: 市场板块筛选值或 `all`。
            listing_status: 上市状态筛选值或 `all`。
            limit: 返回条数上限。
            offset: 分页偏移量。

        Returns:
            命中的标的列表与总数。
        """

        filters: list[str] = []
        params: list[Any] = []
        keyword = query.strip()
        if keyword:
            filters.append("(code LIKE ? OR name LIKE ? OR symbol LIKE ?)")
            like_value = f"%{keyword}%"
            params.extend([like_value, like_value, like_value])
        if instrument_type != "all":
            filters.append("instrument_type = ?")
            params.append(instrument_type)
        if market_board != "all":
            filters.append("market_board = ?")
            params.append(market_board)
        if listing_status != "all":
            filters.append("listing_status = ?")
            params.append(listing_status)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        with self._session() as connection:
            total_row = connection.execute(
                f"SELECT COUNT(*) AS count FROM market_stock_instrument {where_clause}",
                params,
            ).fetchone()
            rows = connection.execute(
                f"""
                SELECT i.symbol, i.code, i.exchange, i.name, i.instrument_type,
                       i.market_board, i.listing_status, i.updated_at
                FROM market_stock_instrument AS i
                {where_clause}
                ORDER BY
                    CASE instrument_type WHEN 'stock' THEN 0 ELSE 1 END,
                    code ASC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        latest_prices = self._load_latest_prices([str(row["symbol"]) for row in rows])
        return (
            [self._build_instrument(row, latest_price=latest_prices.get(str(row["symbol"]))) for row in rows],
            int(total_row["count"]) if total_row else 0,
        )

    def get_instrument(self, symbol: str) -> StockInstrument | None:
        """按带交易所后缀的 symbol 读取标的。"""

        with self._session() as connection:
            row = connection.execute(
                """
                SELECT symbol, code, exchange, name, instrument_type, market_board, listing_status, updated_at
                FROM market_stock_instrument
                WHERE symbol = ?
                """,
                (symbol,),
            ).fetchone()
        return self._build_instrument(row) if row else None

    def upsert_daily_bars(self, symbol: str, bars: Sequence[Mapping[str, Any]]) -> int:
        """幂等写入单只股票日线行情。

        Args:
            symbol: 带交易所后缀的股票代码。
            bars: 按交易日标准化后的行情点。

        Returns:
            本次处理的日线点数量。
        """

        timestamp = _utc_now()
        rows = [
            (
                symbol,
                str(item["trade_date"]),
                float(item["open_price"]),
                float(item["close_price"]),
                float(item["high_price"]),
                float(item["low_price"]),
                float(item["volume"]),
                _optional_float(item.get("ma5")),
                _optional_float(item.get("ma10")),
                _optional_float(item.get("ma20")),
                _optional_float(item.get("ma60")),
                _optional_float(item.get("ma120")),
                _optional_float(item.get("pe_ttm")),
                _optional_float(item.get("pb_mrq")),
                _optional_float(item.get("dividend_yield_ttm")),
                _optional_float(item.get("total_market_cap")),
                str(item.get("provider_key", "akshare")),
                str(item.get("source_url", "https://akshare.akfamily.xyz/")),
                timestamp,
            )
            for item in bars
        ]
        with self._daily_bar_session(symbol) as connection:
            connection.executemany(
                """
                INSERT INTO market_stock_daily_bar (
                    symbol, trade_date, open_price, close_price, high_price, low_price,
                    volume, ma5, ma10, ma20, ma60, ma120, pe_ttm, pb_mrq,
                    dividend_yield_ttm, total_market_cap, provider_key, source_url, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, trade_date) DO UPDATE SET
                    open_price=excluded.open_price,
                    close_price=excluded.close_price,
                    high_price=excluded.high_price,
                    low_price=excluded.low_price,
                    volume=excluded.volume,
                    ma5=excluded.ma5,
                    ma10=excluded.ma10,
                    ma20=excluded.ma20,
                    ma60=excluded.ma60,
                    ma120=excluded.ma120,
                    pe_ttm=COALESCE(excluded.pe_ttm, market_stock_daily_bar.pe_ttm),
                    pb_mrq=COALESCE(excluded.pb_mrq, market_stock_daily_bar.pb_mrq),
                    dividend_yield_ttm=COALESCE(
                        excluded.dividend_yield_ttm,
                        market_stock_daily_bar.dividend_yield_ttm
                    ),
                    total_market_cap=COALESCE(
                        excluded.total_market_cap,
                        market_stock_daily_bar.total_market_cap
                    ),
                    provider_key=excluded.provider_key,
                    source_url=excluded.source_url,
                    last_seen_at=excluded.last_seen_at
                """,
                rows,
            )
        with self._session() as connection:
            self._refresh_stock_sync_state(connection, symbol, timestamp, warning_message="")
        return len(rows)

    def has_daily_bars(self, symbol: str) -> bool:
        """判断某只股票是否已有任意日线数据。"""

        with self._daily_bar_session(symbol) as connection:
            row = connection.execute(
                "SELECT 1 FROM market_stock_daily_bar WHERE symbol = ? LIMIT 1",
                (symbol,),
            ).fetchone()
        return row is not None

    def has_daily_bar_window(self, *, symbol: str, start_date: str, end_date: str) -> bool:
        """判断某只标的的本地日线是否已覆盖指定日期窗口。

        Args:
            symbol: 带交易所后缀的标的代码。
            start_date: 需要覆盖的窗口起始日期，格式为 `YYYY-MM-DD`。
            end_date: 需要覆盖的窗口结束日期，格式为 `YYYY-MM-DD`。

        Returns:
            本地最早日线不晚于起始日期，且最新日线不早于结束日期时返回 `True`。
        """

        with self._daily_bar_session(symbol) as connection:
            row = connection.execute(
                """
                SELECT MIN(trade_date) AS earliest_trade_date,
                       MAX(trade_date) AS latest_trade_date
                FROM market_stock_daily_bar
                WHERE symbol = ?
                """,
                (symbol,),
            ).fetchone()
        if row is None or row["earliest_trade_date"] is None or row["latest_trade_date"] is None:
            return False
        return str(row["earliest_trade_date"]) <= start_date and str(row["latest_trade_date"]) >= end_date

    def load_daily_bars(self, *, symbol: str, start_date: str, end_date: str) -> list[StockDailyBar]:
        """读取指定日期窗口内的日线行情。"""

        with self._daily_bar_session(symbol) as connection:
            rows = connection.execute(
                """
                SELECT symbol, trade_date, open_price, close_price, high_price, low_price,
                       volume, ma5, ma10, ma20, ma60, ma120, pe_ttm, pb_mrq,
                       dividend_yield_ttm, total_market_cap
                FROM market_stock_daily_bar
                WHERE symbol = ? AND trade_date >= ? AND trade_date <= ?
                ORDER BY trade_date ASC
                """,
                (symbol, start_date, end_date),
            ).fetchall()
        return [self._build_daily_bar(row) for row in rows]

    def upsert_profile(self, profile: Mapping[str, Any]) -> None:
        """写入公司概况、板块和股票属性。"""

        timestamp = _utc_now()
        attributes = profile.get("attributes", [])
        encoded_attributes = json.dumps(attributes if isinstance(attributes, list) else [], ensure_ascii=False)
        symbol = str(profile["symbol"])
        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO market_stock_profile (
                    symbol, company_name, industry, sector, region, listing_date,
                    attributes_json, summary, provider_key, source_url, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    company_name=excluded.company_name,
                    industry=excluded.industry,
                    sector=excluded.sector,
                    region=excluded.region,
                    listing_date=excluded.listing_date,
                    attributes_json=excluded.attributes_json,
                    summary=excluded.summary,
                    provider_key=excluded.provider_key,
                    source_url=excluded.source_url,
                    updated_at=excluded.updated_at
                """,
                (
                    symbol,
                    str(profile.get("company_name", "")),
                    str(profile.get("industry", "")),
                    str(profile.get("sector", "")),
                    str(profile.get("region", "")),
                    str(profile.get("listing_date", "")),
                    encoded_attributes,
                    str(profile.get("summary", "")),
                    str(profile.get("provider_key", "akshare")),
                    str(profile.get("source_url", "https://akshare.akfamily.xyz/")),
                    timestamp,
                ),
            )
            self._upsert_stock_sync_state(
                connection,
                symbol,
                timestamp,
                profile_status="live",
                financial_status=None,
                warning_message=None,
            )

    def get_profile(self, symbol: str) -> StockProfile | None:
        """读取股票公司概况。"""

        with self._session() as connection:
            row = connection.execute(
                """
                SELECT symbol, company_name, industry, sector, region, listing_date,
                       attributes_json, summary, updated_at
                FROM market_stock_profile
                WHERE symbol = ?
                """,
                (symbol,),
            ).fetchone()
        if row is None:
            return None
        try:
            attributes = json.loads(str(row["attributes_json"] or "[]"))
        except json.JSONDecodeError:
            attributes = []
        return StockProfile(
            symbol=str(row["symbol"]),
            company_name=str(row["company_name"]),
            industry=str(row["industry"]),
            sector=str(row["sector"]),
            region=str(row["region"]),
            listing_date=str(row["listing_date"]),
            attributes=[str(value) for value in attributes if str(value).strip()],
            summary=str(row["summary"]),
            updated_at=str(row["updated_at"]),
        )

    def upsert_financial_metrics(self, symbol: str, metrics: Sequence[Mapping[str, Any]]) -> int:
        """幂等写入财报指标。"""

        timestamp = _utc_now()
        rows = [
            (
                symbol,
                str(item["report_period"]),
                str(item["report_type"]),
                str(item["metric"]),
                str(item["label"]),
                float(item["value"]),
                str(item.get("unit", "亿元")),
                str(item.get("provider_key", "akshare")),
                timestamp,
            )
            for item in metrics
        ]
        with self._session() as connection:
            connection.executemany(
                """
                INSERT INTO market_stock_financial_metric (
                    symbol, report_period, report_type, metric, label, value, unit, provider_key, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, report_period, report_type, metric) DO UPDATE SET
                    label=excluded.label,
                    value=excluded.value,
                    unit=excluded.unit,
                    provider_key=excluded.provider_key,
                    updated_at=excluded.updated_at
                """,
                rows,
            )
            self._upsert_stock_sync_state(
                connection,
                symbol,
                timestamp,
                profile_status=None,
                financial_status="live" if rows else "unavailable",
                warning_message=None,
            )
        return len(rows)

    def has_financial_metrics(
        self,
        symbol: str,
        *,
        required_metrics: Collection[str] | None = None,
    ) -> bool:
        """判断某只股票是否已有财报指标或指定的完整指标集合。

        Args:
            symbol: 带交易所后缀的股票代码。
            required_metrics: 必须全部存在的指标标识；不传时只判断是否有任意指标。

        Returns:
            已满足所需指标条件时返回 `True`。
        """

        with self._session() as connection:
            rows = connection.execute(
                "SELECT DISTINCT metric FROM market_stock_financial_metric WHERE symbol = ?",
                (symbol,),
            ).fetchall()
        existing_metrics = {str(row["metric"]) for row in rows}
        if required_metrics is None:
            return bool(existing_metrics)
        return set(required_metrics) <= existing_metrics

    def load_financial_metrics(self, *, symbol: str, report_type: str) -> list[StockFinancialMetric]:
        """读取季度或年度财报指标。"""

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT symbol, report_period, report_type, metric, label, value, unit
                FROM market_stock_financial_metric
                WHERE symbol = ? AND report_type = ?
                ORDER BY report_period ASC, metric ASC
                """,
                (symbol, report_type),
            ).fetchall()
        return [
            StockFinancialMetric(
                symbol=str(row["symbol"]),
                report_period=str(row["report_period"]),
                report_type=str(row["report_type"]),
                metric=str(row["metric"]),
                label=str(row["label"]),
                value=float(row["value"]),
                unit=str(row["unit"]),
            )
            for row in rows
        ]

    def get_sync_state(self, symbol: str) -> StockSyncState | None:
        """读取单只股票同步状态。"""

        with self._session() as connection:
            row = connection.execute(
                """
                SELECT symbol, latest_trade_date, earliest_trade_date, daily_point_count,
                       profile_status, financial_status, warning_message, synced_at
                FROM market_stock_sync_state
                WHERE symbol = ?
                """,
                (symbol,),
            ).fetchone()
        if row is None:
            return None
        return StockSyncState(
            symbol=str(row["symbol"]),
            latest_trade_date=str(row["latest_trade_date"]) if row["latest_trade_date"] else None,
            earliest_trade_date=str(row["earliest_trade_date"]) if row["earliest_trade_date"] else None,
            daily_point_count=int(row["daily_point_count"]),
            profile_status=str(row["profile_status"]),
            financial_status=str(row["financial_status"]),
            warning_message=str(row["warning_message"]),
            synced_at=str(row["synced_at"]),
        )

    def record_sync_warning(self, symbol: str, warning_message: str) -> None:
        """记录外部同步失败但不删除既有数据。"""

        timestamp = _utc_now()
        with self._session() as connection:
            self._upsert_stock_sync_state(
                connection,
                symbol,
                timestamp,
                profile_status=None,
                financial_status=None,
                warning_message=warning_message,
            )

    def _initialize(self) -> None:
        """创建股票市场所需表和索引。"""

        with self._session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_stock_instrument (
                    symbol TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    name TEXT NOT NULL,
                    instrument_type TEXT NOT NULL CHECK(instrument_type IN ('stock', 'etf', 'lof')),
                    market_board TEXT NOT NULL,
                    listing_status TEXT NOT NULL,
                    source_url TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._migrate_stock_instrument_type_check(connection)
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_market_stock_instrument_search
                ON market_stock_instrument(code, name, instrument_type, market_board, listing_status)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_stock_profile (
                    symbol TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    industry TEXT NOT NULL,
                    sector TEXT NOT NULL,
                    region TEXT NOT NULL,
                    listing_date TEXT NOT NULL,
                    attributes_json TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    provider_key TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(symbol) REFERENCES market_stock_instrument(symbol)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_stock_financial_metric (
                    symbol TEXT NOT NULL,
                    report_period TEXT NOT NULL,
                    report_type TEXT NOT NULL CHECK(report_type IN ('quarterly', 'yearly')),
                    metric TEXT NOT NULL,
                    label TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    provider_key TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(symbol, report_period, report_type, metric),
                    FOREIGN KEY(symbol) REFERENCES market_stock_instrument(symbol)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_market_stock_financial_symbol_type
                ON market_stock_financial_metric(symbol, report_type, report_period)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_stock_sync_state (
                    symbol TEXT PRIMARY KEY,
                    latest_trade_date TEXT,
                    earliest_trade_date TEXT,
                    daily_point_count INTEGER NOT NULL DEFAULT 0,
                    profile_status TEXT NOT NULL DEFAULT 'unavailable',
                    financial_status TEXT NOT NULL DEFAULT 'unavailable',
                    warning_message TEXT NOT NULL DEFAULT '',
                    synced_at TEXT NOT NULL,
                    FOREIGN KEY(symbol) REFERENCES market_stock_instrument(symbol)
                )
                """
            )
        migrate_legacy_market_stock_shards(self._db_path.parent, self._shard_dir)
        if self._precreate_shards:
            initialize_all_market_stock_shards(self._shard_dir)
        self._migrate_legacy_daily_bars()

    def _migrate_stock_instrument_type_check(self, connection: sqlite3.Connection) -> None:
        """迁移旧版标的表的证券类型约束，允许 LOF 标的入库。

        Args:
            connection: 主库事务连接。

        Returns:
            无返回值；旧表已支持 `lof` 时保持幂等。
        """

        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'market_stock_instrument'"
        ).fetchone()
        create_sql = str(row["sql"] if row else "")
        if "'lof'" in create_sql:
            return

        connection.execute("ALTER TABLE market_stock_instrument RENAME TO market_stock_instrument_legacy")
        connection.execute(
            """
            CREATE TABLE market_stock_instrument (
                symbol TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                exchange TEXT NOT NULL,
                name TEXT NOT NULL,
                instrument_type TEXT NOT NULL CHECK(instrument_type IN ('stock', 'etf', 'lof')),
                market_board TEXT NOT NULL,
                listing_status TEXT NOT NULL,
                source_url TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO market_stock_instrument (
                symbol, code, exchange, name, instrument_type, market_board,
                listing_status, source_url, created_at, updated_at
            )
            SELECT symbol, code, exchange, name, instrument_type, market_board,
                   listing_status, source_url, created_at, updated_at
            FROM market_stock_instrument_legacy
            """
        )
        connection.execute("DROP TABLE market_stock_instrument_legacy")

    def _migrate_legacy_daily_bars(self) -> None:
        """将主库旧日线表幂等迁移到分片，校验完成后移除旧表。"""

        with self._session() as connection:
            legacy_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'market_stock_daily_bar'"
            ).fetchone()
            if legacy_table is None:
                return
            symbols = [
                str(row["symbol"])
                for row in connection.execute(
                    "SELECT DISTINCT symbol FROM market_stock_daily_bar ORDER BY symbol"
                ).fetchall()
            ]
            source_columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(market_stock_daily_bar)").fetchall()
            }

        valuation_projection = ", ".join(
            column if column in source_columns else f"NULL AS {column}"
            for column in ("pe_ttm", "pb_mrq", "dividend_yield_ttm", "total_market_cap")
        )

        symbols_by_shard: dict[Path, list[str]] = defaultdict(list)
        for symbol in symbols:
            symbols_by_shard[resolve_market_stock_shard_path(symbol, self._shard_dir)].append(symbol)

        migrated_source_count = 0
        for shard_path, shard_symbols in symbols_by_shard.items():
            initialize_market_stock_shard(shard_path)
            shard_source_count = 0
            with self._session() as source_connection, self._shard_session(shard_path) as shard_connection:
                for start in range(0, len(shard_symbols), 500):
                    symbol_batch = shard_symbols[start : start + 500]
                    placeholders = ", ".join("?" for _ in symbol_batch)
                    batch_source_count = 0
                    source_cursor = source_connection.execute(
                        f"""
                        SELECT symbol, trade_date, open_price, close_price, high_price, low_price,
                               volume, ma5, ma10, ma20, ma60, ma120, {valuation_projection},
                               provider_key, source_url, last_seen_at
                        FROM market_stock_daily_bar
                        WHERE symbol IN ({placeholders})
                        ORDER BY symbol, trade_date
                        """,
                        symbol_batch,
                    )
                    while source_rows := source_cursor.fetchmany(1_000):
                        shard_connection.executemany(
                            """
                            INSERT INTO market_stock_daily_bar (
                                symbol, trade_date, open_price, close_price, high_price, low_price,
                                volume, ma5, ma10, ma20, ma60, ma120, pe_ttm, pb_mrq,
                                dividend_yield_ttm, total_market_cap, provider_key, source_url, last_seen_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(symbol, trade_date) DO UPDATE SET
                                open_price=excluded.open_price,
                                close_price=excluded.close_price,
                                high_price=excluded.high_price,
                                low_price=excluded.low_price,
                                volume=excluded.volume,
                                ma5=excluded.ma5,
                                ma10=excluded.ma10,
                                ma20=excluded.ma20,
                                ma60=excluded.ma60,
                                ma120=excluded.ma120,
                                pe_ttm=COALESCE(excluded.pe_ttm, market_stock_daily_bar.pe_ttm),
                                pb_mrq=COALESCE(excluded.pb_mrq, market_stock_daily_bar.pb_mrq),
                                dividend_yield_ttm=COALESCE(
                                    excluded.dividend_yield_ttm,
                                    market_stock_daily_bar.dividend_yield_ttm
                                ),
                                total_market_cap=COALESCE(
                                    excluded.total_market_cap,
                                    market_stock_daily_bar.total_market_cap
                                ),
                                provider_key=excluded.provider_key,
                                source_url=excluded.source_url,
                                last_seen_at=excluded.last_seen_at
                            """,
                            source_rows,
                        )
                        batch_source_count += len(source_rows)
                    target_count = int(
                        shard_connection.execute(
                            f"SELECT COUNT(*) FROM market_stock_daily_bar WHERE symbol IN ({placeholders})",
                            symbol_batch,
                        ).fetchone()[0]
                    )
                    if target_count < batch_source_count:
                        raise RuntimeError(
                            f"股票日线分片迁移校验失败: shard={shard_path.name}, "
                            f"source={batch_source_count}, target={target_count}"
                        )
                    shard_source_count += batch_source_count
            migrated_source_count += shard_source_count

        with self._session() as connection:
            source_total = int(connection.execute("SELECT COUNT(*) FROM market_stock_daily_bar").fetchone()[0])
            if migrated_source_count != source_total:
                raise RuntimeError(
                    f"股票日线分片迁移总数校验失败: source={source_total}, migrated={migrated_source_count}"
                )
            connection.execute("DROP TABLE market_stock_daily_bar")
        with self._session() as connection:
            connection.execute("VACUUM")

    def _load_latest_prices(self, symbols: Sequence[str]) -> dict[str, float]:
        """按分片批量读取当前页标的的最新收盘价。"""

        symbols_by_shard: dict[Path, list[str]] = defaultdict(list)
        for symbol in symbols:
            symbols_by_shard[resolve_market_stock_shard_path(symbol, self._shard_dir)].append(symbol)

        latest_prices: dict[str, float] = {}
        for shard_path, shard_symbols in symbols_by_shard.items():
            if not shard_path.exists():
                continue
            initialize_market_stock_shard(shard_path)
            placeholders = ", ".join("?" for _ in shard_symbols)
            with self._shard_session(shard_path) as connection:
                rows = connection.execute(
                    f"""
                    SELECT bars.symbol, bars.close_price
                    FROM market_stock_daily_bar AS bars
                    INNER JOIN (
                        SELECT symbol, MAX(trade_date) AS latest_trade_date
                        FROM market_stock_daily_bar
                        WHERE symbol IN ({placeholders})
                        GROUP BY symbol
                    ) AS latest
                    ON latest.symbol = bars.symbol
                    AND latest.latest_trade_date = bars.trade_date
                    """,
                    shard_symbols,
                ).fetchall()
            latest_prices.update({str(row["symbol"]): float(row["close_price"]) for row in rows})
        return latest_prices

    def _refresh_stock_sync_state(self, connection: sqlite3.Connection, symbol: str, timestamp: str, warning_message: str) -> None:
        """基于日线事实表刷新同步状态。"""

        with self._daily_bar_session(symbol) as daily_connection:
            aggregate = daily_connection.execute(
                """
                SELECT MIN(trade_date) AS earliest_trade_date,
                       MAX(trade_date) AS latest_trade_date,
                       COUNT(*) AS daily_point_count
                FROM market_stock_daily_bar
                WHERE symbol = ?
                """,
                (symbol,),
            ).fetchone()
        self._upsert_stock_sync_state(
            connection,
            symbol,
            timestamp,
            profile_status=None,
            financial_status=None,
            warning_message=warning_message,
            earliest_trade_date=aggregate["earliest_trade_date"] if aggregate else None,
            latest_trade_date=aggregate["latest_trade_date"] if aggregate else None,
            daily_point_count=int(aggregate["daily_point_count"]) if aggregate else 0,
        )

    def _upsert_stock_sync_state(
        self,
        connection: sqlite3.Connection,
        symbol: str,
        timestamp: str,
        *,
        profile_status: str | None,
        financial_status: str | None,
        warning_message: str | None,
        earliest_trade_date: str | None = None,
        latest_trade_date: str | None = None,
        daily_point_count: int | None = None,
    ) -> None:
        """局部更新同步状态，未传字段沿用旧值。"""

        existing = connection.execute(
            """
            SELECT latest_trade_date, earliest_trade_date, daily_point_count,
                   profile_status, financial_status, warning_message
            FROM market_stock_sync_state
            WHERE symbol = ?
            """,
            (symbol,),
        ).fetchone()
        next_values = {
            "latest_trade_date": latest_trade_date if latest_trade_date is not None else (existing["latest_trade_date"] if existing else None),
            "earliest_trade_date": earliest_trade_date if earliest_trade_date is not None else (existing["earliest_trade_date"] if existing else None),
            "daily_point_count": daily_point_count if daily_point_count is not None else (int(existing["daily_point_count"]) if existing else 0),
            "profile_status": profile_status if profile_status is not None else (existing["profile_status"] if existing else "unavailable"),
            "financial_status": financial_status if financial_status is not None else (existing["financial_status"] if existing else "unavailable"),
            "warning_message": warning_message if warning_message is not None else (existing["warning_message"] if existing else ""),
        }
        connection.execute(
            """
            INSERT INTO market_stock_sync_state (
                symbol, latest_trade_date, earliest_trade_date, daily_point_count,
                profile_status, financial_status, warning_message, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                latest_trade_date=excluded.latest_trade_date,
                earliest_trade_date=excluded.earliest_trade_date,
                daily_point_count=excluded.daily_point_count,
                profile_status=excluded.profile_status,
                financial_status=excluded.financial_status,
                warning_message=excluded.warning_message,
                synced_at=excluded.synced_at
            """,
            (
                symbol,
                next_values["latest_trade_date"],
                next_values["earliest_trade_date"],
                next_values["daily_point_count"],
                next_values["profile_status"],
                next_values["financial_status"],
                next_values["warning_message"],
                timestamp,
            ),
        )

    def _build_instrument(self, row: sqlite3.Row, *, latest_price: float | None = None) -> StockInstrument:
        """将 SQLite 行转换为标的数据类。"""

        return StockInstrument(
            symbol=str(row["symbol"]),
            code=str(row["code"]),
            exchange=str(row["exchange"]),
            name=str(row["name"]),
            instrument_type=str(row["instrument_type"]),
            market_board=str(row["market_board"]),
            listing_status=str(row["listing_status"]),
            updated_at=str(row["updated_at"]),
            latest_price=latest_price,
        )

    def _build_daily_bar(self, row: sqlite3.Row) -> StockDailyBar:
        """将 SQLite 行转换为日线数据类。"""

        return StockDailyBar(
            symbol=str(row["symbol"]),
            trade_date=str(row["trade_date"]),
            open_price=float(row["open_price"]),
            close_price=float(row["close_price"]),
            high_price=float(row["high_price"]),
            low_price=float(row["low_price"]),
            volume=float(row["volume"]),
            ma5=_optional_float(row["ma5"]),
            ma10=_optional_float(row["ma10"]),
            ma20=_optional_float(row["ma20"]),
            ma60=_optional_float(row["ma60"]),
            ma120=_optional_float(row["ma120"]),
            pe_ttm=_optional_float(row["pe_ttm"]),
            pb_mrq=_optional_float(row["pb_mrq"]),
            dividend_yield_ttm=_optional_float(row["dividend_yield_ttm"]),
            total_market_cap=_optional_float(row["total_market_cap"]),
        )

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        """打开主库事务连接，并在成功时提交。"""

        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    @contextmanager
    def _daily_bar_session(self, symbol: str) -> Iterator[sqlite3.Connection]:
        """按 symbol 打开目标日线分片连接。

        Args:
            symbol: `股票代码.交易所缩写` 格式的标识。

        Yields:
            已启用行对象访问的分片事务连接。
        """

        shard_path = resolve_market_stock_shard_path(symbol, self._shard_dir)
        initialize_market_stock_shard(shard_path)
        with self._shard_session(shard_path) as connection:
            yield connection

    @contextmanager
    def _shard_session(self, shard_path: Path) -> Iterator[sqlite3.Connection]:
        """打开指定分片事务连接，并在成功时提交。

        Args:
            shard_path: 已初始化的分片数据库路径。

        Yields:
            已启用行对象访问的 SQLite 连接。
        """

        connection = sqlite3.connect(shard_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()


def _optional_float(value: object) -> float | None:
    """将可空值转为浮点数。"""

    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
