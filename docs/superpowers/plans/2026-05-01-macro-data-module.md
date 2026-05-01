# Macro Data Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a top-level Macro Data module with category subtabs, SQLite-backed per-indicator tables, API contracts, and ECharts frontend views.

**Architecture:** Backend uses Controller / Service / Repository boundaries. `MacroDataRepository` owns `.data/macro_data.db`, creates eight indicator fact tables plus registry/sync tables, and exposes safe registry-based reads; `MacroDataService` validates tabs/ranges and returns frontend payloads. Frontend adds `/macro-data` route, sidebar directory, React Query hooks, range controls, and chart cards.

**Tech Stack:** Python 3.12, FastAPI, SQLite, pytest, React 18, TypeScript, Vite, React Query, ECharts, Vitest, Testing Library.

---

## File Structure

- Create `src/services/macro_data_repository.py`: SQLite schema, seed data, idempotent upsert, registry lookup, range reads.
- Create `src/services/macro_data_service.py`: tab/range validation, date range resolution, payload composition.
- Modify `src/app/web/fastapi_app.py`: add `/api/frontend/modules/macro-data` and `/api/frontend/modules/macro-data/charts/{chart_id}`.
- Modify `src/app/web/spa_assets.py`: include `/macro-data`.
- Add `tests/test_macro_data_module.py`: repository and API contract tests.
- Create `frontend/src/features/macro-data/**`: API, types, hooks, chart/range/category components.
- Modify `frontend/src/pages/macro-page.tsx`: render the new Macro Data page.
- Modify `frontend/src/app/routes.tsx`: add `/macro-data` and allow it as a default route.
- Modify `frontend/src/shared/config/nav-items.ts`: add top-level Macro Data directory and subtabs.
- Modify `frontend/src/layouts/sidebar-nav.tsx`: add Heroicons icon for Macro Data.
- Add frontend tests for router/nav/page behavior.
- Update `CHANGELOG.md`, `docs/api-contract.md`, and `docs/test-strategy.md`.

## Tasks

### Task 1: Backend Repository And API Contract

**Files:**
- Create: `src/services/macro_data_repository.py`
- Create: `src/services/macro_data_service.py`
- Modify: `src/app/web/fastapi_app.py`
- Modify: `src/app/web/spa_assets.py`
- Test: `tests/test_macro_data_module.py`

- [ ] **Step 1: Write failing repository/API tests**

```python
def test_repository_initializes_per_indicator_tables(tmp_path):
    repository = MacroDataRepository(tmp_path / "macro_data.db")
    table_names = repository.list_table_names()
    assert "macro_nominal_gdp" in table_names
    assert "macro_cpi" in table_names

def test_frontend_macro_data_module_returns_gdp_charts(tmp_path):
    service = MacroDataService(repository=MacroDataRepository(tmp_path / "macro_data.db"))
    client = TestClient(create_fastapi_app(macro_data_service=service))
    response = client.get("/api/frontend/modules/macro-data?tab=gdp")
    assert response.status_code == 200
    assert [chart["id"] for chart in response.json()["charts"]] == ["nominal_gdp", "real_gdp"]
```

- [ ] **Step 2: Verify backend tests fail**

Run: `uv run python -m pytest tests/test_macro_data_module.py -q`

Expected: import or route failures because the repository, service, and endpoints do not exist.

- [ ] **Step 3: Implement repository, service, and routes**

Implement the smallest vertical slice that creates all tables, seeds deterministic sample rows, validates `tab` and `range`, and returns JSON payloads from SQLite.

- [ ] **Step 4: Verify backend tests pass**

Run: `uv run python -m pytest tests/test_macro_data_module.py -q`

Expected: all tests in the file pass.

### Task 2: Frontend Route, Navigation, And Chart Page

**Files:**
- Create: `frontend/src/features/macro-data/api/get-macro-data-module.ts`
- Create: `frontend/src/features/macro-data/api/get-macro-data-chart.ts`
- Create: `frontend/src/features/macro-data/hooks/use-macro-data-module-query.ts`
- Create: `frontend/src/features/macro-data/hooks/use-macro-data-chart-query.ts`
- Create: `frontend/src/features/macro-data/model/macro-data.types.ts`
- Create: `frontend/src/features/macro-data/components/macro-chart-card.tsx`
- Create: `frontend/src/features/macro-data/components/macro-range-control.tsx`
- Modify: `frontend/src/pages/macro-page.tsx`
- Modify: `frontend/src/app/routes.tsx`
- Modify: `frontend/src/shared/config/nav-items.ts`
- Modify: `frontend/src/layouts/sidebar-nav.tsx`
- Test: `frontend/src/app/__tests__/router-shell.test.tsx`
- Test: `frontend/src/features/macro-data/__tests__/macro-page.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

```tsx
it("renders Macro Data with category subtabs and GDP charts", async () => {
  installWorkbenchFetchMock({ macroData: macroDataPayload, macroChart: macroChartPayload });
  renderApp("/macro-data?tab=gdp");
  expect(await screen.findByRole("heading", { name: "Macro Data" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Macro Data > GDP" })).toBeInTheDocument();
  expect(await screen.findByText("名义GDP")).toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: "一年" }).length).toBeGreaterThan(0);
});
```

- [ ] **Step 2: Verify frontend tests fail**

Run: `cmd /c npm run test -- src/app/__tests__/router-shell.test.tsx src/features/macro-data/__tests__/macro-page.test.tsx --run`

Expected: route and module files are missing.

- [ ] **Step 3: Implement frontend vertical slice**

Add route `/macro-data`, directory navigation, Macro Data page, API hooks, range control, and ECharts chart card with loading/empty/error states.

- [ ] **Step 4: Verify frontend tests pass**

Run: `cmd /c npm run test -- src/app/__tests__/router-shell.test.tsx src/features/macro-data/__tests__/macro-page.test.tsx --run`

Expected: targeted frontend tests pass.

### Task 3: Documentation And Regression

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/api-contract.md`
- Modify: `docs/test-strategy.md`

- [ ] **Step 1: Update docs**

Record the new endpoints, SQLite table strategy, and frontend regression commands.

- [ ] **Step 2: Run release gates**

Run:

```bash
uv run python -m pytest tests/test_macro_data_module.py tests/test_frontend_web_shell.py -q
cmd /c npm run test -- src/app/__tests__/router-shell.test.tsx src/features/macro-data/__tests__/macro-page.test.tsx --run
cmd /c npm run build
```

Expected: all commands exit 0.

## Self-Review

- Spec coverage: plan covers top-level navigation, subtabs, SQLite per-indicator tables, module and chart APIs, independent chart ranges, frontend chart rendering, and required docs.
- Placeholder scan: no task relies on undefined behavior; implementation notes point to concrete files and tests.
- Type consistency: tab keys use `gdp | credit | leverage | prices`; range keys use `6m | 1y | 3y | 5y | 10y | custom`; chart IDs match the SQLite registry.
