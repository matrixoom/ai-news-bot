# Macro Data Factors Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the old Macro tab structure with `数据因子`、`数据源矩阵`、`数据模型`, backed by a stable backend payload and focused frontend rendering.

**Architecture:** Keep `/api/frontend/modules/macro` as the only frontend API. Add a backend domain/service/store slice for Macro data factors and source matrix seed data, then adapt the frontend view model and page to the new payload. Provider scraping is out of scope for phase 1; this phase uses deterministic local seed/sample data so UI and contracts are testable.

**Tech Stack:** Python 3.12, FastAPI, SQLite, pytest, React 18, TypeScript, Vite, Vitest, Testing Library, ECharts.

---

### Task 1: Backend Macro Data Factor Payload

**Files:**
- Create: `src/domain/macro_data_factors.py`
- Create: `src/services/macro_data_factor_store.py`
- Create: `src/services/macro_data_factor_service.py`
- Modify: `src/app/web/frontend_payload.py`
- Modify: `src/services/dashboard_service.py`
- Test: `tests/test_task05_macro_monitoring.py`

- [ ] **Step 1: Write failing backend tests**

Add tests asserting:

```python
def test_macro_data_factor_store_seeds_source_matrix():
    with TemporaryDirectory() as tmpdir:
        store = MacroDataFactorStore(Path(tmpdir) / "macro_data_factors.db")
        rows = store.list_source_matrix_rows()

    assert any(row.factor_code == "housing_price" for row in rows)
    assert any(row.factor_code == "household_demand_deposit_growth" and row.availability_status == "degraded" for row in rows)
```

```python
def test_frontend_macro_module_exposes_data_factor_payload():
    client = TestClient(create_fastapi_app())

    response = client.get("/api/frontend/modules/macro")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_factors"]["label"] == "数据因子"
    assert payload["source_matrix"]["label"] == "数据源矩阵"
    assert payload["data_models"]["status"] == "reserved"
    assert payload["module"]["details"] == []
```

- [ ] **Step 2: Run backend tests and verify RED**

Run:

```powershell
pytest tests/test_task05_macro_monitoring.py -q
```

Expected: fail because `MacroDataFactorStore` and new payload fields do not exist.

- [ ] **Step 3: Implement domain dataclasses**

Create dataclasses for factor definitions, source matrix rows, factor series, table rows, payload summary, and module snapshot. Use Chinese comments/docstrings for public classes.

- [ ] **Step 4: Implement SQLite store**

Create tables:

- `macro_factor_definitions`
- `macro_source_availability_matrix`

Seed first-phase factors and source matrix rows idempotently on store initialization.

- [ ] **Step 5: Implement service and payload builder**

Return deterministic sample series/table rows for first-phase factors. Build `data_factors`, `source_matrix`, and `data_models` in `build_frontend_macro_module_payload`.

- [ ] **Step 6: Run backend tests and verify GREEN**

Run:

```powershell
pytest tests/test_task05_macro_monitoring.py -q
```

Expected: pass.

### Task 2: Frontend Macro View Model

**Files:**
- Modify: `frontend/src/features/macro/model/macro-module.types.ts`
- Modify: `frontend/src/features/macro/model/macro-module-adapter.ts`
- Test: `frontend/src/features/macro/__tests__/macro-page.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Update tests to assert old tabs are gone and new tabs render:

```typescript
expect(await screen.findByRole("link", { name: "数据因子" })).toHaveAttribute("aria-current", "page");
expect(screen.getByRole("link", { name: "数据源矩阵" })).toBeInTheDocument();
expect(screen.getByRole("link", { name: "数据模型" })).toBeInTheDocument();
expect(screen.queryByRole("link", { name: "Compare" })).not.toBeInTheDocument();
```

- [ ] **Step 2: Run frontend test and verify RED**

Run:

```powershell
cd frontend
npm test -- src/features/macro/__tests__/macro-page.test.tsx --runInBand
```

Expected: fail because old tabs still render.

- [ ] **Step 3: Replace Macro types and adapter**

Define `data_factors`, `source_matrix`, and `data_models` raw and view-model types. Keep adapter tolerant of missing fields by returning empty arrays.

- [ ] **Step 4: Run frontend model/page tests**

Run the same Vitest command. Expected: tests still fail until page components are updated.

### Task 3: Frontend Macro Page

**Files:**
- Create: `frontend/src/features/macro/components/macro-data-factors-panel.tsx`
- Create: `frontend/src/features/macro/components/macro-source-matrix-panel.tsx`
- Create: `frontend/src/features/macro/components/macro-data-models-panel.tsx`
- Modify: `frontend/src/pages/macro-page.tsx`
- Test: `frontend/src/features/macro/__tests__/macro-page.test.tsx`

- [ ] **Step 1: Implement new panels**

Create simple, data-dense panels:

- `MacroDataFactorsPanel`: factor tabs/list, latest value cards, ECharts trend surface, table rows.
- `MacroSourceMatrixPanel`: summary cards, matrix table, degraded/unavailable reasons.
- `MacroDataModelsPanel`: reserved empty state.

- [ ] **Step 2: Replace Macro page tab routing**

Use `data_factors` as fallback tab. Remove old render branches for `overview`, `compare`, `indicators`, and `sources`.

- [ ] **Step 3: Run frontend tests and verify GREEN**

Run:

```powershell
cd frontend
npm test -- src/features/macro/__tests__/macro-page.test.tsx --runInBand
```

Expected: pass.

### Task 4: Final Verification

**Files:**
- Modify as needed from previous tasks only.

- [ ] **Step 1: Run backend focused tests**

```powershell
pytest tests/test_task05_macro_monitoring.py -q
```

- [ ] **Step 2: Run frontend focused tests**

```powershell
cd frontend
npm test -- src/features/macro/__tests__/macro-page.test.tsx --runInBand
```

- [ ] **Step 3: Commit implementation**

```powershell
git add src frontend/src tests
git commit -m "feat: add macro data factors module"
```

---

## Self-Review

- Spec coverage: covers new top-level tabs, source matrix, backend payload, SQLite seed, frontend panels, and tests.
- Scope boundary: official provider scraping is intentionally excluded from phase 1.
- TDD path: backend and frontend tests are written before implementation.
