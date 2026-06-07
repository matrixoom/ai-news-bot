"""股票日线 SQLite 分片路由与建库工具。"""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3
from typing import Final


SUPPORTED_STOCK_EXCHANGES: Final[tuple[str, ...]] = ("SH", "SZ", "BJ")

MARKET_STOCK_DAILY_BAR_TABLE_SQL: Final[str] = """
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
    pe_ttm REAL,
    pb_mrq REAL,
    dividend_yield_ttm REAL,
    total_market_cap REAL,
    provider_key TEXT NOT NULL,
    source_url TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    PRIMARY KEY(symbol, trade_date)
)
"""

MARKET_STOCK_DAILY_BAR_INDEX_SQL: Final[str] = """
CREATE INDEX IF NOT EXISTS idx_market_stock_daily_bar_symbol_date
ON market_stock_daily_bar(symbol, trade_date)
"""

MARKET_STOCK_DAILY_BAR_OPTIONAL_COLUMNS: Final[dict[str, str]] = {
    "pe_ttm": "REAL",
    "pb_mrq": "REAL",
    "dividend_yield_ttm": "REAL",
    "total_market_cap": "REAL",
}


def resolve_market_stock_shard_name(symbol: str) -> str:
    """根据股票代码和交易所返回分片数据库文件名。

    Args:
        symbol: `股票代码.交易所缩写` 格式的标识，例如 `600519.SH`。

    Returns:
        符合分库规则的 SQLite 文件名。

    Raises:
        ValueError: symbol 格式、股票代码或交易所不合法。
    """

    if not symbol or symbol.count(".") != 1:
        raise ValueError(f"股票 symbol 格式无效: {symbol!r}")
    code, exchange = symbol.split(".", 1)
    if len(code) != 6 or not code.isdigit():
        raise ValueError(f"股票代码必须是 6 位数字: {code!r}")
    if exchange not in SUPPORTED_STOCK_EXCHANGES:
        raise ValueError(f"不支持的股票交易所: {exchange!r}")

    shard_key = code[-1] if exchange == "BJ" else code[3:5]
    return f"market_stock_{exchange}_{shard_key}.db"


def resolve_market_stock_shard_path(symbol: str, shard_dir: str | Path) -> Path:
    """返回指定股票日线分片的完整路径。

    Args:
        symbol: `股票代码.交易所缩写` 格式的标识。
        shard_dir: 分片数据库所在目录。

    Returns:
        目标分片数据库路径。
    """

    _, exchange = symbol.split(".", 1)
    return Path(shard_dir) / exchange / resolve_market_stock_shard_name(symbol)


def iter_market_stock_shard_paths(shard_dir: str | Path) -> list[Path]:
    """按稳定顺序返回全部 210 个预分库路径。

    Args:
        shard_dir: 分片数据库所在目录。

    Returns:
        先 SH、再 SZ、最后 BJ 的全部分片路径。
    """

    directory = Path(shard_dir)
    paths = [
        directory / exchange / f"market_stock_{exchange}_{shard_key:02d}.db"
        for exchange in ("SH", "SZ")
        for shard_key in range(100)
    ]
    paths.extend(directory / "BJ" / f"market_stock_BJ_{shard_key}.db" for shard_key in range(10))
    return paths


def migrate_legacy_market_stock_shards(
    legacy_dir: str | Path,
    shard_dir: str | Path,
) -> list[Path]:
    """将旧扁平分片移动到按交易所划分的新目录。

    Args:
        legacy_dir: 旧分片文件所在目录。
        shard_dir: 新分片根目录，其下包含 SH、SZ、BJ 子目录。

    Returns:
        本次成功移动到新目录的分片路径。

    Raises:
        FileExistsError: 新旧位置同时存在同名非空分片，拒绝覆盖已有数据。
    """

    source_directory = Path(legacy_dir)
    moved_paths: list[Path] = []
    for target_path in iter_market_stock_shard_paths(shard_dir):
        source_path = source_directory / target_path.name
        if not source_path.exists():
            continue
        if target_path.exists():
            if source_path.stat().st_size == 0:
                continue
            raise FileExistsError(
                f"股票日线新旧分片同时存在，拒绝覆盖: source={source_path}, target={target_path}"
            )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.replace(target_path)
        moved_paths.append(target_path)
    return moved_paths


def initialize_market_stock_shard(db_path: str | Path) -> Path:
    """初始化单个股票日线分片的表和索引。

    Args:
        db_path: 待初始化的 SQLite 分片路径。

    Returns:
        已初始化的分片路径。
    """

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(MARKET_STOCK_DAILY_BAR_TABLE_SQL)
        existing_columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(market_stock_daily_bar)").fetchall()
        }
        for column_name, column_type in MARKET_STOCK_DAILY_BAR_OPTIONAL_COLUMNS.items():
            if column_name not in existing_columns:
                connection.execute(
                    f"ALTER TABLE market_stock_daily_bar ADD COLUMN {column_name} {column_type}"
                )
        connection.execute(MARKET_STOCK_DAILY_BAR_INDEX_SQL)
        connection.commit()
    return path


def initialize_all_market_stock_shards(shard_dir: str | Path) -> list[Path]:
    """预建全部股票日线分片数据库。

    Args:
        shard_dir: 分片数据库所在目录。

    Returns:
        已初始化的 210 个分片路径。
    """

    paths = iter_market_stock_shard_paths(shard_dir)
    for path in paths:
        initialize_market_stock_shard(path)
    return paths
