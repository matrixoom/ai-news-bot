"""sqlite-vec 可选扩展加载器。"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class SqliteVecStatus:
    """描述 sqlite-vec 扩展探测结果。

    Args:
        available: 扩展是否可用。
        reason: 不可用原因或成功说明。

    Returns:
        不可变的扩展状态对象。
    """

    available: bool
    reason: str


def probe_sqlite_vec(connection: sqlite3.Connection) -> SqliteVecStatus:
    """探测当前 SQLite 连接是否可加载 sqlite-vec。

    Args:
        connection: 已打开的 SQLite 连接。

    Returns:
        sqlite-vec 可用性状态；不可用时只返回原因，不抛出业务异常。
    """

    try:
        connection.enable_load_extension(True)
    except sqlite3.Error as exc:
        return SqliteVecStatus(available=False, reason=f"enable_load_extension failed: {exc}")

    try:
        connection.load_extension("sqlite_vec")
    except sqlite3.Error as exc:
        return SqliteVecStatus(available=False, reason=f"sqlite_vec unavailable: {exc}")
    finally:
        try:
            connection.enable_load_extension(False)
        except sqlite3.Error:
            pass

    return SqliteVecStatus(available=True, reason="sqlite_vec loaded")
