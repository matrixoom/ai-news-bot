# Macro Data 就业标签页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Macro Data 下新增“就业”子标签页，并展示“中国社会保险基金支出:失业保险:累计值”年度折线图。

**Architecture:** 复用现有 Macro Data 的 Controller / Service / Repository 三层与每指标一表模型。后端新增 `employment` tab 和独立事实表，前端新增 tab 类型、侧栏子目录与测试 mock，图表仍使用现有 `MacroChartCard` 普通折线图。

**Tech Stack:** Python 3.12、FastAPI、SQLite、pytest、React 18、TypeScript、Vitest、Testing Library。

---

### Task 1: 后端指标契约

**Files:**
- Modify: `tests/test_macro_data_module.py`
- Modify: `src/services/macro_data_repository.py`
- Modify: `src/services/macro_data_service.py`

- [ ] **Step 1: Write the failing backend tests**

```python
def test_frontend_macro_data_module_returns_employment_chart(self) -> None:
    """校验就业标签返回失业保险基金支出累计值图表定义。"""
    response = self.client.get("/api/frontend/modules/macro-data?tab=employment")

    self.assertEqual(response.status_code, 200)
    payload = response.json()
    self.assertEqual(payload["tab"], "employment")
    self.assertEqual([chart["id"] for chart in payload["charts"]], ["unemployment_insurance_fund_expense"])
```

- [ ] **Step 2: Run backend test to verify it fails**

Run: `uv run python -m pytest tests/test_macro_data_module.py -q`
Expected: FAIL because `employment` is not an allowed Macro Data tab.

- [ ] **Step 3: Implement minimal backend support**

Add `employment` to tab allow-list, register `unemployment_insurance_fund_expense`, create `macro_unemployment_insurance_fund_expense`, and seed deterministic yearly sample points.

- [ ] **Step 4: Run backend test to verify it passes**

Run: `uv run python -m pytest tests/test_macro_data_module.py -q`
Expected: PASS.

### Task 2: 前端导航与页面

**Files:**
- Modify: `frontend/src/shared/config/nav-items.ts`
- Modify: `frontend/src/features/macro-data/model/macro-data.types.ts`
- Modify: `frontend/src/features/macro-data/__tests__/macro-page.test.tsx`
- Modify: `frontend/src/app/__tests__/router-shell.test.tsx`
- Modify: `frontend/src/app/__tests__/workbench-api-mocks.ts`

- [ ] **Step 1: Write the failing frontend tests**

```typescript
expect(screen.getByRole("link", { name: "就业" })).toBeInTheDocument();
expect(screen.getByRole("link", { name: "Macro Data > 就业" })).toBeInTheDocument();
```

- [ ] **Step 2: Run frontend test to verify it fails**

Run: `cd frontend && cmd /c npm run test -- src/features/macro-data/__tests__/macro-page.test.tsx src/app/__tests__/router-shell.test.tsx --run`
Expected: FAIL because the tab and side navigation item are missing.

- [ ] **Step 3: Implement minimal frontend support**

Add `employment` to `MacroDataTab`, `MACRO_DATA_TABS`, `moduleDirectories`, and test mock payloads.

- [ ] **Step 4: Run frontend test to verify it passes**

Run: `cd frontend && cmd /c npm run test -- src/features/macro-data/__tests__/macro-page.test.tsx src/app/__tests__/router-shell.test.tsx --run`
Expected: PASS.

### Task 3: Documentation and final verification

**Files:**
- Modify: `docs/api-contract.md`
- Modify: `docs/test-strategy.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Document contract change**

Record that `tab` supports `employment`, and that `unemployment_insurance_fund_expense` is an annual employment indicator.

- [ ] **Step 2: Run final verification**

Run:

```bash
uv run python -m pytest tests/test_macro_data_module.py -q
cd frontend && cmd /c npm run test -- src/features/macro-data/__tests__/macro-page.test.tsx src/app/__tests__/router-shell.test.tsx --run
```

Expected: both commands exit 0.
