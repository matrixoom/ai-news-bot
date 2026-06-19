"""修复股票市场标的的证券类型、市场类型和上市状态分类。"""

from __future__ import annotations

from collections import Counter
import sqlite3
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.stock_market_repository import StockMarketRepository  # noqa: E402
from src.services.stock_market_sync_service import (  # noqa: E402
    _board_for_fund_code,
    _board_for_stock_code,
    _exchange_for_code,
    _is_lof_code,
    _listing_status_for_name,
)


def repair_stock_instrument_classification(db_path: str | Path = ".data/market_data.db") -> dict[str, int]:
    """按当前分类规则修复本地标的主表。

    Args:
        db_path: 股票市场主库路径。

    Returns:
        各类修正数量统计。
    """

    # 初始化仓储会先幂等迁移旧 CHECK 约束，确保 LOF 可写入。
    repository = StockMarketRepository(db_path, precreate_shards=False)
    counters: Counter[str] = Counter()
    with sqlite3.connect(repository.db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT symbol, code, exchange, name, instrument_type, market_board, listing_status
            FROM market_stock_instrument
            ORDER BY symbol
            """
        ).fetchall()
        for row in rows:
            code = str(row["code"])
            name = str(row["name"])
            current_type = str(row["instrument_type"])
            next_type = "lof" if _is_lof_code(code) and current_type != "stock" else current_type
            next_exchange = _exchange_for_code(code) or str(row["exchange"])
            if next_type in {"etf", "lof"}:
                next_board = _board_for_fund_code(code, name)
            else:
                next_board = _board_for_stock_code(code)
            next_status = _listing_status_for_name(name)

            updates: list[str] = []
            params: list[str] = []
            for column, value in (
                ("instrument_type", next_type),
                ("exchange", next_exchange),
                ("market_board", next_board),
                ("listing_status", next_status),
            ):
                if str(row[column]) != value:
                    updates.append(f"{column} = ?")
                    params.append(value)
                    counters[column] += 1
            if updates:
                params.append(str(row["symbol"]))
                connection.execute(
                    f"UPDATE market_stock_instrument SET {', '.join(updates)} WHERE symbol = ?",
                    params,
                )
                counters["rows"] += 1
        connection.commit()
    return dict(counters)


if __name__ == "__main__":
    result = repair_stock_instrument_classification()
    print(result)
