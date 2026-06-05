# Event Insight Delivery Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:writing-plans before implementing each work package. Each package must receive its own task-by-task TDD implementation plan. Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to execute the approved package plan.

**Goal:** Incrementally deliver the Event Insight research workflow without changing the existing domestic and international future-event calendar behavior.

**Architecture:** Keep the current `Outlook` future calendar intact and add a separate `event-insight` domain. SQLite remains the fact database, local workers execute durable asynchronous jobs, LLM calls go through a unified task router, and Neo4j remains a rebuildable graph projection. Each package below produces working, testable software and can be reviewed before the next package begins.

**Tech Stack:** Python 3.12, FastAPI, SQLite, FTS5, sqlite-vec, Neo4j Community, React 18, TypeScript, Vite, TanStack Query, Tailwind CSS, Vitest, pytest.

---

## 1. Delivery Rules

The implementation must preserve these invariants in every package:

```text
1. /event-outlook?tab=domestic and /event-outlook?tab=international remain future-event static calendars.
2. Existing timeline_events, EventsOutlookService, EventsOutlookStore, and /api/frontend/modules/event-outlook stay backward compatible.
3. New research features live under the event-insight domain and /api/frontend/modules/event-insight/*.
4. New SQLite facts live in .data/event_insight.db, separate from .data/events_outlook.db.
5. Controller validates and maps HTTP, Service owns business behavior, Repository owns persistence.
6. Every package updates tests and the affected contract documents in the same commit.
7. Each package is implemented on top of a green baseline and committed separately.
```

Before implementing a package:

```text
1. Create a dedicated package implementation plan under docs/superpowers/plans/.
2. Use test-driven development for code changes.
3. Run the package-specific tests.
4. Run the static calendar regression.
5. Run the full backend suite, frontend suite, and frontend build before committing.
```

Required full gate:

```powershell
uv run python -m pytest -q
cd frontend
cmd /c npm run test -- --run
cmd /c npm run build
```

---

## 2. Dependency Graph

```text
P1 Workspace shell and mock pages
  └── Visible frontend review baseline

P0 Technical validation
  ├── P2 SQLite migration foundation
  └── P5 Unified LLM runtime and settings

P2 SQLite migration foundation
  ├── P3 Durable jobs and material import
  └── P4 Event workbench API and live UI

P3 Durable jobs and material import
  └── P6 Event extraction and evidence chain

P5 Unified LLM runtime and settings
  └── P6 Event extraction and evidence chain

P6 Event extraction and evidence chain
  └── P7 Retrieval, deduplication, and topic clustering

P7 Retrieval, deduplication, and topic clustering
  ├── P8 Topic trace page
  └── P9 Graph projection and relationship page

P1 through P9
  └── P10 Hardening, documentation, and release gate
```

Recommended execution:

```text
1. Execute P1 first to deliver the reviewable Mock frontend workbench.
2. Execute P0 before adding database, graph, or LLM production dependencies.
3. Execute P2 after P0.
4. After P2, P3, P4, and P5 can proceed independently.
5. Execute P6 after P3 and P5.
6. Execute P7 after P6.
7. Execute P8 and P9 in parallel after P7.
8. Finish with P10.
```

---

## 3. Package Summary

| Package | Outcome | Depends On | Can Run In Parallel With |
| --- | --- | --- | --- |
| P0 | Verified local technical choices | None | None |
| P1 | New navigation and four mock workbench pages | None | None |
| P2 | Separate SQLite database and migrations | P0 | P1 |
| P3 | Durable local jobs and material import | P2 | P4, P5 |
| P4 | Live event list workbench | P2 | P3, P5 |
| P5 | Unified LLM runtime and settings | P0 | P1, P3, P4 |
| P6 | LLM extraction with traceable evidence | P3, P5 | None |
| P7 | FTS, vectors, duplicate candidates, clustering | P6 | None |
| P8 | Topic trace research page | P7 | P9 |
| P9 | Neo4j projection and relationship graph page | P7 | P8 |
| P10 | Cross-package regression and release documentation | P1-P9 | None |

---

## 4. P0: Technical Validation

**Objective:** Resolve environment-sensitive choices before production code depends on them.

**Scope:**

```text
Verify sqlite-vec loading on Windows + Python 3.12.
Measure FTS5 unicode61 Chinese recall using fixed Chinese finance samples.
Verify Neo4j Community local startup, constraints, projection rebuild, and unavailable behavior.
Compare candidate frontend graph libraries using a small event/entity graph.
Confirm the BaseLLMProvider and ArkResearchProvider unification path.
```

**Files:**

- Create: `docs/superpowers/specs/2026-06-02-event-insight-phase0-validation.md`
- Create: `tests/fixtures/event_insight/chinese_search_samples.json`
- Create: `tests/fixtures/event_insight/graph_projection_samples.json`

**Validation record must include:**

```text
sqlite-vec installation command and extension loading code
sqlite-vec virtual table DDL
Chinese FTS5 recall examples and fallback decision
Neo4j startup command and required environment variables
Chosen graph library with bundle-size and interaction notes
Existing LLM call chains and the approved migration order
```

**Acceptance:**

```powershell
uv run python -m pytest tests/test_event_outlook_timeline.py -q
```

Expected result: existing future calendar regression remains green.

**Commit:**

```text
docs: record event insight technical validation
```

**Stop condition:** Do not add dependencies, production event-insight repositories, APIs, or pages in this package. Record the validated installation commands for later packages.

---

## 5. P1: Workspace Shell And Mock Pages

**Objective:** Add the three research workspace entries and a display-only LLM settings page while keeping the two calendar tabs unchanged.

**Scope:**

```text
Add Outlook > 事件列表.
Add Outlook > 主题溯源.
Add Outlook > 事件关系图.
Route domestic and international to the existing timeline canvas.
Route the three new tabs to mock-backed research page shells.
Add a display-only Settings > 大模型配置 mock workspace.
Do not call new backend APIs yet.
```

**Files:**

- Modify: `frontend/src/shared/config/nav-items.ts`
- Modify: `frontend/src/pages/event-outlook-page.tsx`
- Create: `frontend/src/features/event-insight/model/event-insight.types.ts`
- Create: `frontend/src/features/event-insight/mock/event-insight.mock.ts`
- Create: `frontend/src/features/event-insight/components/event-list-workspace.tsx`
- Create: `frontend/src/features/event-insight/components/topic-trace-workspace.tsx`
- Create: `frontend/src/features/event-insight/components/event-graph-workspace.tsx`
- Modify: `frontend/src/pages/settings-page.tsx`
- Create: `frontend/src/features/settings/components/llm-settings-workspace.tsx`
- Modify: `frontend/src/features/event-outlook/__tests__/event-outlook-page.test.tsx`
- Modify: `frontend/src/app/__tests__/router-shell.test.tsx`
- Modify: `frontend/src/features/settings/__tests__/settings-page.test.tsx`
- Modify: `CHANGELOG.md`

**Key design rule:**

```text
EventOutlookPage resolves the workspace tab first.
Only domestic and international are passed to useEventOutlookModuleQuery.
events, topic-trace, and event-graph render event-insight components without invoking the static calendar API.
```

**Acceptance:**

```powershell
cd frontend
cmd /c npm run test -- src/features/event-outlook/__tests__/event-outlook-page.test.tsx src/features/event-insight/__tests__/event-insight-workspaces.test.tsx src/features/settings/__tests__/settings-page.test.tsx src/app/__tests__/router-shell.test.tsx --run
cmd /c npm run build
```

**Commit:**

```text
feat: add event insight workspace shells
```

**Stop condition:** Pages contain deterministic mock content only. Settings actions are disabled. Do not create SQLite tables or LLM calls.

---

## 6. P2: SQLite Migration Foundation

**Objective:** Introduce a separate, versioned fact database for Event Insight.

**Scope:**

```text
Create .data/event_insight.db.
Add explicit schema_migration support.
Enable foreign_keys and WAL on every repository connection.
Create the first migration with core facts, evidence, overrides, jobs, logs, and graph outbox tables.
Keep sqlite-vec tables out of this migration until P7.
```

**Files:**

- Create: `src/domain/event_insight.py`
- Create: `src/services/event_insight_migrations.py`
- Create: `src/services/event_insight_repository.py`
- Create: `tests/test_event_insight_repository.py`
- Create or update after migration: `.data/event_insight.db`
- Modify: `docs/architecture.md`
- Modify: `docs/test-strategy.md`
- Modify: `CHANGELOG.md`

**Tables in migration `001_event_insight_core`:**

```text
schema_migration
scan_batch
analysis_run
raw_document
raw_document_fts and triggers
event
event_fts and triggers
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

**Repository tests:**

```text
Migration is idempotent.
Foreign keys reject invalid references.
FTS5 insert, update, and archive behavior stays synchronized.
Field overrides are stored independently from model facts.
Duplicate candidates retain source and candidate events.
Outbox idempotency_key prevents duplicate projection work.
```

**Acceptance:**

```powershell
uv run python -m pytest tests/test_event_insight_repository.py tests/test_event_outlook_timeline.py -q
```

**Commit:**

```text
feat: add event insight sqlite foundation
```

**Stop condition:** No HTTP endpoints and no background worker loop are added in this package.

---

## 7. P3: Durable Jobs And Material Import

**Objective:** Accept raw research materials and process them through recoverable local jobs.

**Scope:**

```text
Support URL import metadata, pasted text, and controlled local file upload.
Copy uploaded files into a controlled relative data directory.
Create parse_document jobs with idempotency keys.
Implement atomic job claiming, lease recovery, attempt logs, retry scheduling, and status reads.
Return 202 + jobId for imports.
```

**Files:**

- Create: `src/services/event_insight_job_service.py`
- Create: `src/services/event_insight_import_service.py`
- Create: `src/app/web/event_insight_routes.py`
- Modify: `src/services/event_insight_repository.py`
- Modify: `src/app/web/fastapi_app.py`
- Create: `tests/test_event_insight_jobs.py`
- Create: `tests/test_event_insight_import_api.py`
- Modify: `docs/api-contract.md`
- Modify: `docs/architecture.md`
- Modify: `docs/test-strategy.md`
- Modify: `CHANGELOG.md`

**API:**

```http
POST /api/frontend/modules/event-insight/documents/import
GET /api/frontend/modules/event-insight/jobs/{jobId}
```

**Security rules:**

```text
Validate MIME, extension, file size, and content hash.
Persist only controlled relative file paths.
Reject path traversal.
Do not fetch remote URL bodies inside the request thread.
```

**Acceptance:**

```powershell
uv run python -m pytest tests/test_event_insight_jobs.py tests/test_event_insight_import_api.py tests/test_event_outlook_timeline.py -q
```

**Commit:**

```text
feat: add durable event insight import jobs
```

**Stop condition:** Parsing may store normalized text, but event extraction and LLM calls remain disabled.

---

## 8. P4: Event List Workbench

**Objective:** Deliver a useful manual event-management workbench before automatic analysis is available.

**Scope:**

```text
Add event list, event detail, edit, ignore, topic-create, topic-link, and batch-action APIs.
Support filtering, sorting, pagination, traceId, and partial-success batch responses.
Replace the mock event-list page with React Query-backed data.
Add filters, table, detail drawer, edit dialog, and batch action bar.
```

**Files:**

- Create: `src/services/event_insight_service.py`
- Modify: `src/services/event_insight_repository.py`
- Modify: `src/app/web/event_insight_routes.py`
- Create: `tests/test_event_insight_api.py`
- Create: `frontend/src/features/event-insight/api/get-events.ts`
- Create: `frontend/src/features/event-insight/api/get-event-detail.ts`
- Create: `frontend/src/features/event-insight/api/update-event.ts`
- Create: `frontend/src/features/event-insight/api/run-event-batch-action.ts`
- Create: `frontend/src/features/event-insight/hooks/use-event-insight-events-query.ts`
- Create: `frontend/src/features/event-insight/components/event-filter-bar.tsx`
- Create: `frontend/src/features/event-insight/components/event-table.tsx`
- Create: `frontend/src/features/event-insight/components/event-detail-drawer.tsx`
- Modify: `frontend/src/features/event-insight/components/event-list-workspace.tsx`
- Create: `frontend/src/features/event-insight/__tests__/event-list-workspace.test.tsx`
- Modify: `docs/api-contract.md`
- Modify: `CHANGELOG.md`

**API:**

```http
GET /api/frontend/modules/event-insight/events
GET /api/frontend/modules/event-insight/events/{eventId}
PUT /api/frontend/modules/event-insight/events/{eventId}
POST /api/frontend/modules/event-insight/events/{eventId}/ignore
POST /api/frontend/modules/event-insight/topics
POST /api/frontend/modules/event-insight/events/{eventId}/link-topic
POST /api/frontend/modules/event-insight/events/batch-action
```

**Acceptance:**

```powershell
uv run python -m pytest tests/test_event_insight_api.py tests/test_event_outlook_timeline.py -q
cd frontend
cmd /c npm run test -- src/features/event-insight/__tests__/event-list-workspace.test.tsx src/features/event-outlook/__tests__/event-outlook-page.test.tsx --run
```

**Commit:**

```text
feat: add event insight list workbench
```

**Stop condition:** The workbench edits manually seeded or imported facts. Automatic extraction remains outside this package.

---

## 9. P5: Unified LLM Runtime And Settings

**Objective:** Add configurable, task-routed model access without creating a third LLM call chain.

**Scope:**

```text
Extend BaseLLMProvider with base_url, timeout, structured output, and embeddings.
Add OpenAI-compatible provider construction.
Persist encrypted provider settings and task mappings.
Expose provider list, save, disable, connection-test, and task-mapping APIs.
Add Settings > 大模型配置.
Adapt ArkResearchProvider to the unified client factory without changing calendar output.
```

**Files:**

- Modify: `src/llm_providers/base_provider.py`
- Modify: `src/llm_providers/openai_provider.py`
- Modify: `src/llm_providers/deepseek_provider.py`
- Modify: `src/llm_providers/__init__.py`
- Create: `src/llm_providers/openai_compatible_provider.py`
- Create: `src/security/local_secret_cipher.py`
- Create: `src/services/llm_config_repository.py`
- Create: `src/services/llm_config_service.py`
- Create: `src/services/llm_task_router.py`
- Modify: `src/services/event_insight_migrations.py`
- Create or update after migration: `.data/event_insight.db`
- Modify: `src/providers/live_data.py`
- Create: `src/app/web/llm_settings_routes.py`
- Modify: `src/app/web/fastapi_app.py`
- Create: `tests/test_llm_task_router.py`
- Create: `tests/test_llm_settings_api.py`
- Modify: `frontend/src/pages/settings-page.tsx`
- Create: `frontend/src/features/settings/components/llm-provider-table.tsx`
- Create: `frontend/src/features/settings/components/llm-provider-edit-dialog.tsx`
- Create: `frontend/src/features/settings/components/llm-task-mapping-table.tsx`
- Modify: `frontend/src/features/settings/__tests__/settings-page.test.tsx`
- Modify: `docs/api-contract.md`
- Modify: `docs/architecture.md`
- Modify: `CHANGELOG.md`

**API:**

```http
GET /api/system/llm/providers
POST /api/system/llm/providers
PUT /api/system/llm/providers/{id}
POST /api/system/llm/providers/{id}/disable
POST /api/system/llm/providers/{id}/test
GET /api/system/llm/task-configs
PUT /api/system/llm/task-configs/{taskType}
```

**Security tests:**

```text
API keys are encrypted at rest.
List and edit responses never expose plaintext keys.
Logs do not include plaintext keys or full request headers.
Disabling an in-use provider returns 409 provider_in_use.
ArkResearchProvider still produces the existing future calendar contract.
```

**Migration:**

```text
002_llm_runtime
  llm_provider_config
  llm_task_config
  llm_call_log
```

**Acceptance:**

```powershell
uv run python -m pytest tests/test_llm_task_router.py tests/test_llm_settings_api.py tests/test_event_outlook_timeline.py -q
cd frontend
cmd /c npm run test -- src/features/settings/__tests__/settings-page.test.tsx --run
```

**Commit:**

```text
feat: add task-routed llm settings
```

**Stop condition:** No event extraction prompt is added in this package.

---

## 10. P6: Event Extraction And Evidence Chain

**Objective:** Convert parsed materials into schema-validated events with source-position evidence.

**Scope:**

```text
Add centralized prompt templates and JSON Schemas.
Process extract_event jobs through LlmTaskRouter.
Validate model output before writing facts.
Store analysis_run, llm_call_log, event_source, evidence, event_evidence, entities, and aliases.
Show evidence excerpts and source locations in the event drawer.
Support re-extract as a new analysis run.
```

**Files:**

- Create: `src/prompts/event_insight/event_extraction.md`
- Create: `src/schemas/event_insight/event_extraction.schema.json`
- Create: `src/services/event_extraction_service.py`
- Modify: `src/services/event_insight_job_service.py`
- Modify: `src/services/event_insight_repository.py`
- Modify: `src/services/event_insight_service.py`
- Create: `tests/fixtures/event_insight/storage_price_material.txt`
- Create: `tests/test_event_extraction_service.py`
- Modify: `tests/test_event_insight_jobs.py`
- Modify: `frontend/src/features/event-insight/components/event-detail-drawer.tsx`
- Modify: `frontend/src/features/event-insight/__tests__/event-list-workspace.test.tsx`
- Modify: `docs/api-contract.md`
- Modify: `docs/architecture.md`
- Modify: `CHANGELOG.md`

**Failure paths:**

```text
LLM timeout
rate limit
non-JSON output
JSON Schema validation failure
evidence excerpt not found in raw material
```

**Acceptance:**

```powershell
uv run python -m pytest tests/test_event_extraction_service.py tests/test_event_insight_jobs.py tests/test_event_insight_api.py -q
cd frontend
cmd /c npm run test -- src/features/event-insight/__tests__/event-list-workspace.test.tsx --run
```

**Commit:**

```text
feat: extract events with traceable evidence
```

**Stop condition:** Similarity search, automatic duplicate confirmation, and topic trace generation remain disabled.

---

## 11. P7: Retrieval, Deduplication, And Topic Clustering

**Objective:** Add high-quality search and candidate generation without destructive automatic merging.

**Scope:**

```text
Add raw-document and event keyword search through FTS5.
Load sqlite-vec using the P0-validated approach.
Store model name, dimension, content hash, and vectors.
Generate duplicate_event_candidate rows from weighted similarity.
Confirm or reject duplicate candidates without deleting events.
Cluster events into topics and preserve manual topic assignments.
```

**Files:**

- Create: `src/services/sqlite_vec_loader.py`
- Create: `src/services/event_insight_search_repository.py`
- Create: `src/services/event_deduplication_service.py`
- Create: `src/services/topic_clustering_service.py`
- Modify: `src/services/event_insight_migrations.py`
- Modify: `requirements.txt`
- Modify: `src/services/event_insight_job_service.py`
- Modify: `src/services/event_insight_repository.py`
- Create: `tests/test_event_insight_search.py`
- Create: `tests/test_event_deduplication_service.py`
- Create: `tests/test_topic_clustering_service.py`
- Modify: `docs/architecture.md`
- Modify: `docs/test-strategy.md`
- Modify: `CHANGELOG.md`

**Acceptance:**

```powershell
uv run python -m pytest tests/test_event_insight_search.py tests/test_event_deduplication_service.py tests/test_topic_clustering_service.py tests/test_event_outlook_timeline.py -q
```

**Commit:**

```text
feat: add event insight retrieval and clustering
```

**Stop condition:** Do not add Neo4j writes in this package.

---

## 12. P8: Topic Trace Page

**Objective:** Deliver the research timeline for one topic using SQLite facts and evidence.

**Scope:**

```text
Add keyword and topic trace queries.
Build summary, lifecycle stage, timeline roles, risks, and evidence lists.
Run topic re-analysis asynchronously and return 202 + analysisRunId.
Replace the mock topic-trace page with React Query-backed data.
Support manual event role corrections.
```

**Files:**

- Create: `src/prompts/event_insight/topic_summary.md`
- Create: `src/prompts/event_insight/lifecycle_stage_judgement.md`
- Create: `src/prompts/event_insight/risk_detection.md`
- Create: `src/schemas/event_insight/topic_summary.schema.json`
- Create: `src/services/topic_trace_service.py`
- Modify: `src/services/event_insight_job_service.py`
- Modify: `src/services/event_insight_service.py`
- Modify: `src/app/web/event_insight_routes.py`
- Create: `tests/test_topic_trace_service.py`
- Create: `tests/test_topic_trace_api.py`
- Create: `frontend/src/features/event-insight/api/get-topic-trace.ts`
- Create: `frontend/src/features/event-insight/api/analyze-topic.ts`
- Create: `frontend/src/features/event-insight/hooks/use-topic-trace-query.ts`
- Create: `frontend/src/features/event-insight/components/topic-summary-card.tsx`
- Create: `frontend/src/features/event-insight/components/event-timeline.tsx`
- Create: `frontend/src/features/event-insight/components/evidence-list.tsx`
- Create: `frontend/src/features/event-insight/components/risk-panel.tsx`
- Modify: `frontend/src/features/event-insight/components/topic-trace-workspace.tsx`
- Create: `frontend/src/features/event-insight/__tests__/topic-trace-workspace.test.tsx`
- Modify: `docs/api-contract.md`
- Modify: `CHANGELOG.md`

**API:**

```http
GET /api/frontend/modules/event-insight/topics/trace
POST /api/frontend/modules/event-insight/topics/analyze
PUT /api/frontend/modules/event-insight/topics/{topicId}/events/{eventId}
POST /api/frontend/modules/event-insight/topics/{topicId}/events/{eventId}/unlink
```

**Acceptance:**

```powershell
uv run python -m pytest tests/test_topic_trace_service.py tests/test_topic_trace_api.py -q
cd frontend
cmd /c npm run test -- src/features/event-insight/__tests__/topic-trace-workspace.test.tsx --run
```

**Commit:**

```text
feat: add event insight topic trace
```

---

## 13. P9: Graph Projection And Relationship Page

**Objective:** Add rebuildable Neo4j projection and an interactive relationship graph without making Neo4j a source of truth.

**Scope:**

```text
Generate candidate event relations before LLM judgement.
Store relation evidence in SQLite.
Write graph_sync_outbox rows in the same SQLite transaction as facts.
Consume outbox rows idempotently into Neo4j.
Support projection rebuild and degraded reads when Neo4j is unavailable.
Replace the mock graph page with nodes, edges, details, filters, and bounded path trace.
```

**Files:**

- Create: `src/prompts/event_insight/relation_judgement.md`
- Create: `src/schemas/event_insight/relation_judgement.schema.json`
- Create: `src/services/event_relation_service.py`
- Create: `src/services/event_graph_projection_repository.py`
- Create: `src/services/event_graph_service.py`
- Modify: `src/services/event_insight_job_service.py`
- Modify: `src/services/event_insight_repository.py`
- Modify: `src/app/web/event_insight_routes.py`
- Create: `tests/test_event_relation_service.py`
- Create: `tests/test_event_graph_projection.py`
- Create: `tests/test_event_graph_api.py`
- Create: `frontend/src/features/event-insight/api/get-topic-graph.ts`
- Create: `frontend/src/features/event-insight/api/get-event-path.ts`
- Create: `frontend/src/features/event-insight/components/event-graph-canvas.tsx`
- Create: `frontend/src/features/event-insight/components/graph-filter-panel.tsx`
- Create: `frontend/src/features/event-insight/components/node-detail-drawer.tsx`
- Create: `frontend/src/features/event-insight/components/edge-detail-drawer.tsx`
- Create: `frontend/src/features/event-insight/components/path-trace-panel.tsx`
- Modify: `frontend/src/features/event-insight/components/event-graph-workspace.tsx`
- Create: `frontend/src/features/event-insight/__tests__/event-graph-workspace.test.tsx`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `docs/api-contract.md`
- Modify: `docs/architecture.md`
- Modify: `CHANGELOG.md`

**API:**

```http
GET /api/frontend/modules/event-insight/graph/topic/{topicId}
GET /api/frontend/modules/event-insight/relations/{relationId}
POST /api/frontend/modules/event-insight/relations
PUT /api/frontend/modules/event-insight/relations/{relationId}
POST /api/frontend/modules/event-insight/relations/{relationId}/archive
GET /api/frontend/modules/event-insight/graph/path
```

**Acceptance:**

```powershell
uv run python -m pytest tests/test_event_relation_service.py tests/test_event_graph_projection.py tests/test_event_graph_api.py -q
cd frontend
cmd /c npm run test -- src/features/event-insight/__tests__/event-graph-workspace.test.tsx --run
cmd /c npm run build
```

**Commit:**

```text
feat: add event insight graph projection
```

**Stop condition:** Neo4j remains optional. Event list and topic trace must continue to function while Neo4j is stopped.

---

## 14. P10: Hardening, Documentation, And Release Gate

**Objective:** Close cross-package gaps and prove the vertical slice works end to end.

**Scope:**

```text
Run the full fixed-fixture workflow:
import -> parse -> extract -> evidence -> embedding -> duplicate candidate -> topic -> relation -> graph projection.

Verify static calendar regression.
Verify Neo4j unavailable degradation.
Verify encrypted API key handling.
Verify local-time formatting.
Verify migration from an empty database and repeated startup.
Update all project documentation and changelog entries.
```

**Files:**

- Create: `tests/test_event_insight_vertical_slice.py`
- Create: `frontend/src/features/event-insight/__tests__/event-insight-smoke.test.tsx`
- Modify: `docs/api-contract.md`
- Modify: `docs/architecture.md`
- Modify: `docs/test-strategy.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Release gate:**

```powershell
uv run python -m pytest -q
cd frontend
cmd /c npm run test -- --run
cmd /c npm run build
```

Manual verification:

```text
1. Open /event-outlook?tab=domestic and verify the future calendar is unchanged.
2. Open /event-outlook?tab=events and import the fixed storage-price fixture.
3. Verify the extracted event opens evidence at the expected source location.
4. Open /event-outlook?tab=topic-trace and verify the generated timeline.
5. Open /event-outlook?tab=event-graph and verify nodes, edges, details, and bounded path trace.
6. Stop Neo4j and verify the list and topic trace still work while the graph shows degradation.
```

**Acceptance:** The automated release gate and all six manual checks pass before the package commit.

**Commit:**

```text
test: harden event insight vertical slice
```

---

## 15. Risk Register

| Risk | Earliest Package | Mitigation |
| --- | --- | --- |
| sqlite-vec fails to load on Windows | P0 | Validate before schema adoption; keep FTS5-only fallback |
| `unicode61` recall is weak for Chinese text | P0 | Measure fixed samples; use application n-gram support if required |
| New workspace accidentally passes `events` as calendar region | P1 | Add frontend regression asserting no static-calendar request occurs |
| Migration order breaks foreign keys | P2 | Test empty database initialization and repeated startup |
| Background jobs duplicate facts after restart | P3 | Use idempotency keys, leases, and attempt logs |
| LLM settings leak API keys | P5 | Encrypt at rest, redact responses, assert logs contain no plaintext |
| Model output invents evidence | P6 | Require evidence excerpt lookup against stored raw material |
| Deduplication destroys research history | P7 | Store candidates and canonical links; never hard-delete source events |
| Neo4j outage blocks research pages | P9 | Keep SQLite as source of truth and test degraded reads |
| Graph library inflates bundle or becomes unreadable | P0, P9 | Select library in P0 and test a bounded topic subgraph |

---

## 16. Review Checkpoints

Review after each checkpoint:

```text
Checkpoint A: P0
  Confirm local technology choices.

Checkpoint B: P1 + P2
  Confirm navigation, isolation from static calendar, and database ownership.

Checkpoint C: P3 + P4 + P5
  Confirm the manual workbench, durable jobs, and LLM configuration before enabling analysis.

Checkpoint D: P6 + P7
  Confirm extraction quality, evidence traceability, retrieval, and non-destructive deduplication.

Checkpoint E: P8 + P9
  Confirm research usefulness of topic trace and graph projection.

Checkpoint F: P10
  Confirm release readiness.
```

The first implementation plan is:

```text
docs/superpowers/plans/2026-06-02-event-insight-i1-frontend-workbench.md
```
