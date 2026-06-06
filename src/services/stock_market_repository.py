"""A 股股票市场本地 SQLite 仓储。"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Mapping, Sequence


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


class StockMarketRepository:
    """管理股票市场相关表的读写。"""

    def __init__(self, db_path: str | Path = ".data/market_data.db") -> None:
        """初始化仓储并确保表结构存在。

        Args:
            db_path: SQLite 数据库路径。

        Returns:
            已完成建表的仓储实例。
        """

        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
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
                SELECT i.symbol, i.code, i.exchange, i.name, i.instrument_type, i.market_board, i.listing_status, i.updated_at,
                       (
                           SELECT b.close_price
                           FROM market_stock_daily_bar AS b
                           WHERE b.symbol = i.symbol
                           ORDER BY b.trade_date DESC
                           LIMIT 1
                       ) AS latest_price
                FROM market_stock_instrument AS i
                {where_clause}
                ORDER BY
                    CASE instrument_type WHEN 'stock' THEN 0 ELSE 1 END,
                    code ASC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        return [self._build_instrument(row) for row in rows], int(total_row["count"]) if total_row else 0

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
                str(item.get("provider_key", "akshare")),
                str(item.get("source_url", "https://akshare.akfamily.xyz/")),
                timestamp,
            )
            for item in bars
        ]
        with self._session() as connection:
            connection.executemany(
                """
                INSERT INTO market_stock_daily_bar (
                    symbol, trade_date, open_price, close_price, high_price, low_price,
                    volume, ma5, ma10, ma20, ma60, ma120, provider_key, source_url, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    provider_key=excluded.provider_key,
                    source_url=excluded.source_url,
                    last_seen_at=excluded.last_seen_at
                """,
                rows,
            )
            self._refresh_stock_sync_state(connection, symbol, timestamp, warning_message="")
        return len(rows)

    def has_daily_bars(self, symbol: str) -> bool:
        """判断某只股票是否已有任意日线数据。"""

        with self._session() as connection:
            row = connection.execute(
                "SELECT 1 FROM market_stock_daily_bar WHERE symbol = ? LIMIT 1",
                (symbol,),
            ).fetchone()
        return row is not None

    def load_daily_bars(self, *, symbol: str, start_date: str, end_date: str) -> list[StockDailyBar]:
        """读取指定日期窗口内的日线行情。"""

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT symbol, trade_date, open_price, close_price, high_price, low_price,
                       volume, ma5, ma10, ma20, ma60, ma120
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

    def has_financial_metrics(self, symbol: str) -> bool:
        """判断某只股票是否已有财报指标。"""

        with self._session() as connection:
            row = connection.execute(
                "SELECT 1 FROM market_stock_financial_metric WHERE symbol = ? LIMIT 1",
                (symbol,),
            ).fetchone()
        return row is not None

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
                    instrument_type TEXT NOT NULL CHECK(instrument_type IN ('stock', 'etf')),
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
                CREATE INDEX IF NOT EXISTS idx_market_stock_instrument_search
                ON market_stock_instrument(code, name, instrument_type, market_board, listing_status)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_stock_daily_bar (
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
                    PRIMARY KEY(symbol, trade_date),
                    FOREIGN KEY(symbol) REFERENCES market_stock_instrument(symbol)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_market_stock_daily_bar_symbol_date
                ON market_stock_daily_bar(symbol, trade_date)
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

    def _refresh_stock_sync_state(self, connection: sqlite3.Connection, symbol: str, timestamp: str, warning_message: str) -> None:
        """基于日线事实表刷新同步状态。"""

        aggregate = connection.execute(
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

    def _build_instrument(self, row: sqlite3.Row) -> StockInstrument:
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
            latest_price=_optional_float(row["latest_price"]) if "latest_price" in row.keys() else None,
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
        )

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._db_path)
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
