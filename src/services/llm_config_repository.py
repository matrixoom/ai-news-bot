"""LLM 配置 SQLite 仓储。"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from .event_insight_migrations import EventInsightMigrationService, utc_now_iso


class LlmConfigRepository:
    """管理 LLM provider 与任务映射配置。

    Args:
        db_path: Event Insight SQLite 数据库路径。

    Returns:
        初始化后的仓储实例。
    """

    def __init__(self, db_path: str | Path = ".data/event_insight.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        EventInsightMigrationService(self._db_path).apply()

    def create_provider(self, values: dict[str, Any]) -> dict[str, Any]:
        """新增模型 provider 配置。"""

        timestamp = utc_now_iso()
        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO llm_provider_config (
                    name, provider_type, base_url, model_name, encrypted_api_key,
                    timeout_seconds, supports_structured_output, supports_embeddings,
                    enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    values["name"],
                    values["provider_type"],
                    values.get("base_url", ""),
                    values["model_name"],
                    values.get("encrypted_api_key", ""),
                    values.get("timeout_seconds", 60),
                    int(values.get("supports_structured_output", True)),
                    int(values.get("supports_embeddings", False)),
                    timestamp,
                    timestamp,
                ),
            )
        return self.get_provider(int(cursor.lastrowid)) or {}

    def update_provider(self, provider_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        """更新模型 provider 配置。"""

        existing = self.get_provider(provider_id)
        if existing is None:
            return None
        merged = {**existing, **values, "updated_at": utc_now_iso()}
        with self._session() as connection:
            connection.execute(
                """
                UPDATE llm_provider_config
                SET name = ?, provider_type = ?, base_url = ?, model_name = ?,
                    encrypted_api_key = ?, timeout_seconds = ?,
                    supports_structured_output = ?, supports_embeddings = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    merged["name"],
                    merged["provider_type"],
                    merged.get("base_url", ""),
                    merged["model_name"],
                    merged.get("encrypted_api_key", ""),
                    int(merged.get("timeout_seconds") or 60),
                    int(merged.get("supports_structured_output") or 0),
                    int(merged.get("supports_embeddings") or 0),
                    merged["updated_at"],
                    provider_id,
                ),
            )
        return self.get_provider(provider_id)

    def list_providers(self) -> list[dict[str, Any]]:
        """列出全部 provider 配置。"""

        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM llm_provider_config ORDER BY enabled DESC, id ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_provider(self, provider_id: int) -> dict[str, Any] | None:
        """按主键读取 provider 配置。"""

        with self._session() as connection:
            row = connection.execute("SELECT * FROM llm_provider_config WHERE id = ?", (provider_id,)).fetchone()
        return dict(row) if row else None

    def disable_provider(self, provider_id: int) -> dict[str, Any] | None:
        """禁用 provider 配置。"""

        timestamp = utc_now_iso()
        with self._session() as connection:
            cursor = connection.execute(
                """
                UPDATE llm_provider_config
                SET enabled = 0, disabled_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (timestamp, timestamp, provider_id),
            )
        return self.get_provider(provider_id) if cursor.rowcount else None

    def provider_has_task_mapping(self, provider_id: int) -> bool:
        """判断 provider 是否被任务映射引用。"""

        with self._session() as connection:
            row = connection.execute(
                "SELECT 1 FROM llm_task_config WHERE provider_config_id = ? LIMIT 1",
                (provider_id,),
            ).fetchone()
        return row is not None

    def upsert_task_config(self, task_type: str, values: dict[str, Any]) -> dict[str, Any]:
        """新增或更新任务模型映射。"""

        timestamp = utc_now_iso()
        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO llm_task_config (
                    task_type, provider_config_id, model_name, temperature, max_tokens, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_type) DO UPDATE SET
                    provider_config_id = excluded.provider_config_id,
                    model_name = excluded.model_name,
                    temperature = excluded.temperature,
                    max_tokens = excluded.max_tokens,
                    updated_at = excluded.updated_at
                """,
                (
                    task_type,
                    values["provider_config_id"],
                    values.get("model_name", ""),
                    values.get("temperature", 0.2),
                    values.get("max_tokens", 2000),
                    timestamp,
                ),
            )
        return self.get_task_config(task_type) or {}

    def list_task_configs(self) -> list[dict[str, Any]]:
        """列出任务模型映射。"""

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT tc.*, pc.name AS provider_name, pc.provider_type, pc.enabled
                FROM llm_task_config tc
                JOIN llm_provider_config pc ON pc.id = tc.provider_config_id
                ORDER BY tc.task_type ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_task_config(self, task_type: str) -> dict[str, Any] | None:
        """读取单个任务模型映射。"""

        with self._session() as connection:
            row = connection.execute(
                """
                SELECT tc.*, pc.name AS provider_name, pc.provider_type, pc.enabled
                FROM llm_task_config tc
                JOIN llm_provider_config pc ON pc.id = tc.provider_config_id
                WHERE tc.task_type = ?
                """,
                (task_type,),
            ).fetchone()
        return dict(row) if row else None

    def _connect(self) -> sqlite3.Connection:
        """打开 SQLite 连接。"""

        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        """打开 Repository 会话并在退出时提交。"""

        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()
