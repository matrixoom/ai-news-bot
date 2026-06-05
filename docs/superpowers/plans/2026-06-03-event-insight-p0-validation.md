# Event Insight P0 Technical Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 验证 Event Insight 后续会依赖的本地技术选择，并把结论固化为可复查的工程记录。

**Architecture:** P0 不新增生产代码、不改接口、不引入持久依赖，只通过本地命令验证 sqlite-vec、SQLite FTS5、Neo4j 可用性、前端图谱库选择和 LLM Provider 统一路径。验证结果写入 specs 文档，固定中文检索和图谱投影后续实现边界。

**Tech Stack:** Python 3.12, SQLite FTS5, sqlite-vec, Neo4j Community, React 18, ECharts, pytest.

---

## 1. File Map

```text
docs/superpowers/specs/2026-06-02-event-insight-phase0-validation.md
  P0 技术验证记录，包含命令、输出摘要、结论和后续包约束。

tests/fixtures/event_insight/chinese_search_samples.json
  P7 检索测试可复用的中文财经样本。

tests/fixtures/event_insight/graph_projection_samples.json
  P9 图谱投影测试可复用的事件、实体、主题和关系样本。

CHANGELOG.md
  记录 P0 技术验证结论。
```

## 2. Task Sequence

### Task 1: Record The P0 Plan

**Files:**

- Create: `docs/superpowers/plans/2026-06-03-event-insight-p0-validation.md`

- [x] **Step 1: Create this package-level implementation plan**

Record the verification work as a standalone increment so later packages can cite the exact P0 result.

- [x] **Step 2: Run static calendar baseline**

```powershell
uv run python -m pytest tests/test_event_outlook_timeline.py -q
```

Expected: existing Outlook future-calendar regression passes.

### Task 2: Validate SQLite Search And Vector Choices

**Files:**

- Create: `tests/fixtures/event_insight/chinese_search_samples.json`
- Modify: `docs/superpowers/specs/2026-06-02-event-insight-phase0-validation.md`

- [x] **Step 1: Validate sqlite-vec import and virtual table DDL**

```powershell
uv run --with sqlite-vec python -c "import sqlite3, sqlite_vec; print(sqlite3.sqlite_version); print(sqlite_vec.__version__)"
```

Then create a `vec0` table with:

```sql
CREATE VIRTUAL TABLE event_embedding USING vec0(
  event_id integer primary key,
  embedding float[4]
);
```

Expected: sqlite-vec loads and returns nearest-neighbor rows.

- [x] **Step 2: Validate native FTS5 unicode61 recall**

Use fixed Chinese samples for HBM, memory price, optical module and gold topics. Expected: `unicode61` matches ASCII-like tokens such as `HBM4`, but does not reliably recall Chinese short phrases such as `内存` or `涨价`.

- [x] **Step 3: Validate application n-gram fallback**

Add a generated `grams` column for 2-gram and 3-gram terms. Expected: Chinese phrases such as `内存`, `存储芯片`, `涨价`, `先进封装`, and `AI服务器` recall the expected sample rows.

### Task 3: Validate Graph And LLM Integration Boundaries

**Files:**

- Create: `tests/fixtures/event_insight/graph_projection_samples.json`
- Modify: `docs/superpowers/specs/2026-06-02-event-insight-phase0-validation.md`

- [x] **Step 1: Check Neo4j local availability**

```powershell
docker --version
```

Expected in the current environment: Docker is unavailable. P9 must treat Neo4j as optional and support degraded reads.

- [x] **Step 2: Compare frontend graph library candidates**

Inspect current dependencies:

```powershell
node -e "const lock=require('./frontend/package-lock.json'); console.log(lock.packages['node_modules/echarts']?.version)"
```

Expected: ECharts 6 is already present; Cytoscape, G6 and React Flow are absent. P9 should start with ECharts graph unless interaction requirements exceed it.

- [x] **Step 3: Confirm LLM unification path**

Inspect `src/llm_providers/base_provider.py`, OpenAI-compatible providers, and `ArkResearchProvider`. Expected: P5 should add one task router and OpenAI-compatible provider factory, then adapt Ark through that factory instead of creating a third call chain.

### Task 4: Document And Verify P0

**Files:**

- Create: `docs/superpowers/specs/2026-06-02-event-insight-phase0-validation.md`
- Modify: `CHANGELOG.md`

- [x] **Step 1: Write the validation record**

The record must include sqlite-vec installation command, virtual table DDL, FTS5 examples, Neo4j startup command, graph library decision and LLM migration order.

- [x] **Step 2: Run acceptance regression**

```powershell
uv run python -m pytest tests/test_event_outlook_timeline.py -q
```

Expected: existing future calendar regression remains green.

- [x] **Step 3: Run full gate before commit**

```powershell
uv run python -m pytest -q
cmd /c npm --prefix frontend run test -- --run
cmd /c npm --prefix frontend run build
```

Expected: backend tests, frontend tests and frontend build pass.

- [x] **Step 4: Commit the isolated increment**

```text
docs: record event insight technical validation
```

## 3. Stop Condition

P0 ends with documentation and fixtures only. Do not add production Event Insight repositories, database migrations, HTTP endpoints, LLM calls, Neo4j clients, or new frontend graph dependencies in this increment.
