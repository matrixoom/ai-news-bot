# Event Insight P4 Event List Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Mock 事件列表替换为真实 API 支撑的人工事件管理工作台。

**Architecture:** 后端新增 `EventInsightService` 作为业务层，`event_insight_routes.py` 继续作为 Controller，`EventInsightRepository` 负责 SQLite 查询和写入。前端新增 `features/event-insight/api` 与 `hooks`，事件列表页通过 React Query 加载真实数据并支持选择详情。

**Tech Stack:** Python 3.12, FastAPI, SQLite, React 18, TanStack Query, Tailwind CSS, Vitest, pytest.

---

## 1. File Map

```text
src/services/event_insight_repository.py
  增加事件列表、详情、更新、忽略、主题和批量操作数据方法。

src/services/event_insight_service.py
  实现事件工作台业务规则、分页、过滤、traceId 和部分成功批量响应。

src/app/web/event_insight_routes.py
  注册事件列表、详情、编辑、忽略、主题创建、主题关联、批量操作 API。

src/app/web/fastapi_app.py
  注入 EventInsightService。

tests/test_event_insight_api.py
  覆盖 P4 后端 API 契约与静态日历隔离。

frontend/src/features/event-insight/api/get-events.ts
frontend/src/features/event-insight/api/get-event-detail.ts
frontend/src/features/event-insight/api/update-event.ts
frontend/src/features/event-insight/api/run-event-batch-action.ts
frontend/src/features/event-insight/hooks/use-event-insight-events-query.ts
frontend/src/features/event-insight/hooks/use-event-detail-query.ts
  前端 API 与 React Query hooks。

frontend/src/features/event-insight/components/event-filter-bar.tsx
frontend/src/features/event-insight/components/event-table.tsx
frontend/src/features/event-insight/components/event-detail-drawer.tsx
frontend/src/features/event-insight/components/event-list-workspace.tsx
frontend/src/features/event-insight/__tests__/event-list-workspace.test.tsx
  替换 Mock 列表为真实 API 工作台。

frontend/src/app/__tests__/workbench-api-mocks.ts
  增加 Event Insight API mock。

docs/api-contract.md
docs/test-strategy.md
CHANGELOG.md
  记录 P4 契约、回归方式和变更。
```

## 2. Task Sequence

### Task 1: Backend API Red Tests

**Files:**

- Create: `tests/test_event_insight_api.py`

- [x] **Step 1: Write failing API tests**

Cover:

```text
GET /events returns filtered paginated events
GET /events/{eventId} returns evidence and topics
PUT /events/{eventId} edits manual fields without deleting facts
POST /events/{eventId}/ignore soft ignores an event
POST /topics creates topic
POST /events/{eventId}/link-topic links event to topic
POST /events/batch-action returns partial success
existing Outlook static calendar still works
```

- [x] **Step 2: Run focused backend tests and verify RED**

```powershell
uv run python -m pytest tests/test_event_insight_api.py -q
```

Expected: FAIL because P4 routes/service do not exist.

### Task 2: Backend Implementation

**Files:**

- Modify: `src/services/event_insight_repository.py`
- Create: `src/services/event_insight_service.py`
- Modify: `src/app/web/event_insight_routes.py`
- Modify: `src/app/web/fastapi_app.py`

- [x] **Step 1: Implement repository query/mutation methods**

Add list/detail/update/ignore/topic/batch helpers.

- [x] **Step 2: Implement service contract**

Return stable API payloads with `traceId`, pagination and partial-success batch results.

- [x] **Step 3: Register routes**

Add `/api/frontend/modules/event-insight/events*` and topic routes.

- [x] **Step 4: Run focused backend tests**

Expected: PASS.

### Task 3: Frontend Red Tests

**Files:**

- Create: `frontend/src/features/event-insight/__tests__/event-list-workspace.test.tsx`
- Modify: `frontend/src/app/__tests__/workbench-api-mocks.ts`

- [x] **Step 1: Write failing frontend tests**

Cover:

```text
event list workspace loads /api/frontend/modules/event-insight/events
event detail request fires when selecting another row
loading and empty states are visible
```

- [x] **Step 2: Run focused frontend tests and verify RED**

```powershell
cmd /c npm --prefix frontend run test -- src/features/event-insight/__tests__/event-list-workspace.test.tsx --run
```

Expected: FAIL because component is still mock-backed.

### Task 4: Frontend Implementation

**Files:**

- Create: `frontend/src/features/event-insight/api/get-events.ts`
- Create: `frontend/src/features/event-insight/api/get-event-detail.ts`
- Create: `frontend/src/features/event-insight/api/update-event.ts`
- Create: `frontend/src/features/event-insight/api/run-event-batch-action.ts`
- Create: `frontend/src/features/event-insight/hooks/use-event-insight-events-query.ts`
- Create: `frontend/src/features/event-insight/hooks/use-event-detail-query.ts`
- Create: `frontend/src/features/event-insight/components/event-filter-bar.tsx`
- Create: `frontend/src/features/event-insight/components/event-table.tsx`
- Create: `frontend/src/features/event-insight/components/event-detail-drawer.tsx`
- Modify: `frontend/src/features/event-insight/components/event-list-workspace.tsx`

- [x] **Step 1: Implement API and hooks**

Use fetch, throw on non-OK response, and keep query keys stable.

- [x] **Step 2: Replace mock list with query-backed UI**

Keep the P1 visual structure, add loading/empty/error states.

- [x] **Step 3: Run focused frontend tests**

Expected: PASS.

### Task 5: Verify And Commit P4

**Files:**

- Modify: `docs/api-contract.md`
- Modify: `docs/test-strategy.md`
- Modify: `CHANGELOG.md`

- [x] **Step 1: Run package gate**

```powershell
uv run python -m pytest tests/test_event_insight_api.py tests/test_event_insight_repository.py tests/test_event_outlook_timeline.py -q
cmd /c npm --prefix frontend run test -- src/features/event-insight/__tests__/event-list-workspace.test.tsx src/features/event-outlook/__tests__/event-outlook-page.test.tsx --run
```

- [x] **Step 2: Run full gate**

```powershell
uv run python -m pytest -q
cmd /c npm --prefix frontend run test -- --run
cmd /c npm --prefix frontend run build
```

- [ ] **Step 3: Commit**

```text
feat: add event insight list workbench
```

## 3. Stop Condition

P4 ends with a useful manual event workbench. Automatic extraction, vector search, topic trace generation and graph projection remain outside this increment.
