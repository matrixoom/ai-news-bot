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

    return Path(shard_dir) / resolve_market_stock_shard_name(symbol)


def iter_market_stock_shard_paths(shard_dir: str | Path) -> list[Path]:
    """按稳定顺序返回全部 210 个预分库路径。

    Args:
        shard_dir: 分片数据库所在目录。

    Returns:
        先 SH、再 SZ、最后 BJ 的全部分片路径。
    """

    directory = Path(shard_dir)
    paths = [
        directory / f"market_stock_{exchange}_{shard_key:02d}.db"
        for exchange in ("SH", "SZ")
        for shard_key in range(100)
    ]
    paths.extend(directory / f"market_stock_BJ_{shard_key}.db" for shard_key in range(10))
    return paths


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
