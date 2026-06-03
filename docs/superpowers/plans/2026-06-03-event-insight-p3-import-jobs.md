# Event Insight P3 Import Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 支持原始研究材料导入，并为后续解析/抽取建立可恢复的本地任务队列。

**Architecture:** P3 在 P2 Repository 地基上新增 JobService、ImportService 和 FastAPI 路由。HTTP Controller 只做 payload/header 转换和错误码映射；Service 负责导入校验、受控文件复制、幂等键和任务创建；Repository 负责 SQLite 读写、任务领取、租约恢复和 attempt 日志。

**Tech Stack:** Python 3.12, FastAPI, SQLite, pytest/unittest, local filesystem.

---

## 1. File Map

```text
src/services/event_insight_repository.py
  增加 raw_document hash 查询、processing_job 创建/读取/领取/失败重试方法。

src/services/event_insight_job_service.py
  封装任务创建、状态读取、原子领取、完成和失败重试。

src/services/event_insight_import_service.py
  校验 URL / text / file JSON 导入，复制受控文件，创建 raw_document 和 parse_document job。

src/app/web/event_insight_routes.py
  注册 /api/frontend/modules/event-insight/documents/import 和 /jobs/{jobId}。

src/app/web/fastapi_app.py
  注入并注册 Event Insight routes。

tests/test_event_insight_jobs.py
  覆盖任务幂等、领取、租约恢复、attempt 日志和失败重试。

tests/test_event_insight_import_api.py
  覆盖 text/url/file 导入、路径穿越拒绝、job 状态和静态日历隔离。

docs/api-contract.md
docs/architecture.md
docs/test-strategy.md
CHANGELOG.md
  记录 P3 API、架构和回归门禁。
```

## 2. Task Sequence

### Task 1: Write Job Service Red Tests

**Files:**

- Create: `tests/test_event_insight_jobs.py`

- [x] **Step 1: Add failing job tests**

Cover:

```text
create_job returns the same job for the same idempotency key
claim_next_job marks a job running and records attempt 1
claim_next_job does not claim an active lease
expired running lease can be claimed again and attempt_count increments
fail_job schedules retry while attempts remain and marks failed after max attempts
```

- [x] **Step 2: Run focused test and verify RED**

```powershell
uv run python -m pytest tests/test_event_insight_jobs.py -q
```

Expected: FAIL because `event_insight_job_service` does not exist.

### Task 2: Write Import API Red Tests

**Files:**

- Create: `tests/test_event_insight_import_api.py`

- [x] **Step 1: Add failing API tests**

Cover:

```text
POST text import returns 202 + jobId and stores raw_document
POST URL import stores URL metadata without fetching remote content
POST file import copies into a controlled relative data directory
file import rejects path traversal
GET job returns status payload
existing Event Outlook static calendar route still works
```

- [x] **Step 2: Run focused test and verify RED**

```powershell
uv run python -m pytest tests/test_event_insight_import_api.py -q
```

Expected: FAIL because routes and services do not exist.

### Task 3: Implement Job Repository And Service

**Files:**

- Modify: `src/services/event_insight_repository.py`
- Create: `src/services/event_insight_job_service.py`

- [x] **Step 1: Add Repository job methods**

Implement processing_job insert/read/list-attempt/claim/fail/complete helpers.

- [x] **Step 2: Add JobService**

Implement service-facing job creation, status payloads and lease handling.

- [x] **Step 3: Run job tests**

```powershell
uv run python -m pytest tests/test_event_insight_jobs.py -q
```

Expected: PASS.

### Task 4: Implement Import Service And API

**Files:**

- Create: `src/services/event_insight_import_service.py`
- Create: `src/app/web/event_insight_routes.py`
- Modify: `src/app/web/fastapi_app.py`
- Modify: `src/services/event_insight_repository.py`

- [x] **Step 1: Add import validation and storage**

Implement text, url and controlled JSON file imports. Reject path traversal, unsupported MIME/extension and over-limit content.

- [x] **Step 2: Register FastAPI routes**

Register:

```http
POST /api/frontend/modules/event-insight/documents/import
GET /api/frontend/modules/event-insight/jobs/{jobId}
```

- [x] **Step 3: Run API tests**

```powershell
uv run python -m pytest tests/test_event_insight_import_api.py -q
```

Expected: PASS.

### Task 5: Verify And Document P3

**Files:**

- Modify: `docs/api-contract.md`
- Modify: `docs/architecture.md`
- Modify: `docs/test-strategy.md`
- Modify: `CHANGELOG.md`

- [x] **Step 1: Run package gate**

```powershell
uv run python -m pytest tests/test_event_insight_jobs.py tests/test_event_insight_import_api.py tests/test_event_outlook_timeline.py -q
```

Expected: P3 tests and static calendar regression pass.

- [x] **Step 2: Run full gate**

```powershell
uv run python -m pytest -q
cmd /c npm --prefix frontend run test -- --run
cmd /c npm --prefix frontend run build
```

Expected: backend tests, frontend tests and frontend build pass.

- [x] **Step 3: Commit the isolated increment**

```text
feat: add durable event insight import jobs
```

## 3. Stop Condition

P3 ends with import APIs and recoverable local jobs. Parsing may store normalized text, but event extraction, LLM calls, embeddings, clustering and graph projection remain disabled.
