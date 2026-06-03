# Event Insight P2 SQLite Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Event Insight 建立独立、可迁移、可测试的 SQLite 事实库。

**Architecture:** 新增 `event_insight` 领域模型、migration service 和 repository，默认写入 `.data/event_insight.db`，与现有 `.data/events_outlook.db` 完全隔离。P2 只创建数据库地基和 Repository 能力，不新增 HTTP 路由、后台 worker、LLM 调用或 Neo4j 写入。

**Tech Stack:** Python 3.12, SQLite, FTS5, pytest/unittest.

---

## 1. File Map

```text
src/domain/event_insight.py
  定义 Event Insight 事件、原始材料、证据、人工覆盖、重复候选和 outbox 的轻量数据模型。

src/services/event_insight_migrations.py
  管理 schema_migration 和 001_event_insight_core，负责幂等建表、索引、触发器、PRAGMA。

src/services/event_insight_repository.py
  提供 Repository 会话、迁移入口和 P2 可验证的基础写读方法。

tests/test_event_insight_repository.py
  覆盖 migration 幂等、外键、FTS 同步、人工覆盖、重复候选和 outbox 幂等。

.data/event_insight.db
  由迁移生成的第一阶段事实库，随本地历史数据一起提交。

docs/architecture.md
  记录 Event Insight 独立数据库和三层边界。

docs/test-strategy.md
  记录 Event Insight 数据层回归门禁。

CHANGELOG.md
  记录 P2 增量。
```

## 2. Task Sequence

### Task 1: Write Repository Red Tests

**Files:**

- Create: `tests/test_event_insight_repository.py`

- [x] **Step 1: Add failing repository tests**

Cover these behaviors:

```python
repository = EventInsightRepository(self.db_path)
self.assertIn("event", repository.list_table_names())
self.assertEqual(repository.list_applied_migrations(), ["001_event_insight_core"])
```

Also cover foreign key rejection, raw document FTS update/archive, event FTS update/archive, field override persistence, duplicate candidate persistence and outbox idempotency.

- [x] **Step 2: Run the focused test and verify RED**

```powershell
uv run python -m pytest tests/test_event_insight_repository.py -q
```

Expected: FAIL because `src.services.event_insight_repository` does not exist.

### Task 2: Implement Migration Foundation

**Files:**

- Create: `src/services/event_insight_migrations.py`
- Create: `src/domain/event_insight.py`

- [x] **Step 1: Add migration service**

Create `EventInsightMigrationService.apply()` with `PRAGMA foreign_keys=ON`, `PRAGMA journal_mode=WAL`, `schema_migration` and `001_event_insight_core`.

- [x] **Step 2: Add all P2 tables**

Create:

```text
schema_migration
scan_batch
analysis_run
raw_document
raw_document_fts
event
event_fts
event_source
evidence
event_evidence
entity
entity_alias
event_entity
topic
topic_event
event_relation
relation_evidence
event_operation_log
event_field_override
duplicate_event_candidate
processing_job
processing_job_attempt
graph_sync_outbox
graph_projection_state
```

- [x] **Step 3: Add FTS triggers and core indexes**

Raw documents and events must be removed from FTS when archived.

### Task 3: Implement Repository Methods

**Files:**

- Create: `src/services/event_insight_repository.py`

- [x] **Step 1: Add connection/session helpers**

Every connection must enable `foreign_keys` and `WAL`, set `row_factory=sqlite3.Row`, and commit/close deterministically.

- [x] **Step 2: Add document/event/evidence helpers**

Implement deterministic methods used by tests:

```text
create_raw_document
update_raw_document_content
archive_raw_document
search_raw_documents
create_event
update_event_summary
archive_event
search_events
create_evidence
link_event_evidence
```

- [x] **Step 3: Add override, duplicate and outbox helpers**

Implement:

```text
create_event_field_override
list_event_field_overrides
create_duplicate_event_candidate
list_duplicate_event_candidates
enqueue_graph_sync
list_graph_outbox
```

### Task 4: Verify And Document P2

**Files:**

- Create or update: `.data/event_insight.db`
- Modify: `docs/architecture.md`
- Modify: `docs/test-strategy.md`
- Modify: `CHANGELOG.md`

- [x] **Step 1: Run focused repository tests**

```powershell
uv run python -m pytest tests/test_event_insight_repository.py tests/test_event_outlook_timeline.py -q
```

Expected: Event Insight repository and static calendar regression pass.

- [x] **Step 2: Create the default database**

```powershell
uv run python -c "from src.services.event_insight_repository import EventInsightRepository; EventInsightRepository('.data/event_insight.db')"
```

Expected: `.data/event_insight.db` exists and has migration `001_event_insight_core`.

- [x] **Step 3: Run full gate before commit**

```powershell
uv run python -m pytest -q
cmd /c npm --prefix frontend run test -- --run
cmd /c npm --prefix frontend run build
```

Expected: backend tests, frontend tests and frontend build pass.

- [x] **Step 4: Commit the isolated increment**

```text
feat: add event insight sqlite foundation
```

## 3. Stop Condition

P2 ends with a migrated SQLite database and Repository tests. Do not add HTTP endpoints, background worker loops, sqlite-vec tables, LLM calls, Neo4j clients or frontend API integration.
