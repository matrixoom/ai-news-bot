# Event Insight I1 Frontend Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 先交付四个可浏览、可测试的 Mock 前端工作台页面，并保证现有国内 / 国际未来事件日历完全不变。

**Architecture:** 在现有 React SPA 中新增 `features/event-insight` 目录，以类型文件、确定性 Mock 数据和三个独立工作区组件承载事件洞察页面。`EventOutlookPage` 先解析工作区 Tab，仅在 `domestic | international` 时挂载原有静态日历子组件；`SettingsPage` 增加 Mock 大模型配置页面。第一阶段不新增后端接口，不引入图谱依赖。

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS, Heroicons, Vitest, Testing Library.

---

## 1. File Map

```text
frontend/src/features/event-outlook/components/event-outlook-calendar-workspace.tsx
  从 EventOutlookPage 提取现有静态日历，实现行为保持不变。

frontend/src/features/event-insight/model/event-insight.types.ts
  定义 Mock 工作台展示模型。

frontend/src/features/event-insight/mock/event-insight.mock.ts
  存放确定性演示数据，不发起后端请求。

frontend/src/features/event-insight/components/event-insight-shell.tsx
  提供新增页面共用的标题、操作区和基础面板样式。

frontend/src/features/event-insight/components/event-list-workspace.tsx
  渲染事件表格和详情抽屉。

frontend/src/features/event-insight/components/topic-trace-workspace.tsx
  渲染摘要卡片、阶段条、演进时间线和待验证线索。

frontend/src/features/event-insight/components/event-graph-workspace.tsx
  渲染关系过滤、静态图谱画布和节点详情。

frontend/src/features/settings/components/llm-settings-workspace.tsx
  渲染大模型服务列表、Mock 配置表单和任务映射表。
```

## 2. Task Sequence

### Task 1: Protect Calendar Routing And Add Navigation

**Files:**

- Modify: `frontend/src/shared/config/nav-items.ts`
- Modify: `frontend/src/pages/event-outlook-page.tsx`
- Create: `frontend/src/features/event-outlook/components/event-outlook-calendar-workspace.tsx`
- Modify: `frontend/src/features/event-outlook/__tests__/event-outlook-page.test.tsx`
- Modify: `frontend/src/app/__tests__/router-shell.test.tsx`

- [ ] **Step 1: Write failing route-isolation tests**

```tsx
it("renders the event insight list without requesting the static calendar", async () => {
  const fetchMock = installWorkbenchFetchMock();
  renderEventOutlookApp("/event-outlook?tab=events");
  expect(await screen.findByRole("heading", { name: "事件列表" })).toBeInTheDocument();
  expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/api/frontend/modules/event-outlook"))).toBe(false);
});
```

Add sidebar assertions for `事件列表`, `主题溯源`, and `事件关系图`.

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
cmd /c npm --prefix frontend run test -- src/features/event-outlook/__tests__/event-outlook-page.test.tsx src/app/__tests__/router-shell.test.tsx --run
```

Expected: FAIL because the new navigation and workspace route do not exist.

- [ ] **Step 3: Extract the current static calendar and add guarded routing**

Move the current timeline query, mutations, filters and dialogs into `EventOutlookCalendarWorkspace`. Keep `EventOutlookPage` responsible for resolving:

```ts
type EventOutlookWorkspaceTab = "domestic" | "international" | "events" | "topic-trace" | "event-graph";
```

Render the static component only for `domestic | international`.

- [ ] **Step 4: Run focused tests and verify pass**

Run the Task 1 command. Expected: PASS.

### Task 2: Build Mock Event Insight Workspaces

**Files:**

- Create: `frontend/src/features/event-insight/model/event-insight.types.ts`
- Create: `frontend/src/features/event-insight/mock/event-insight.mock.ts`
- Create: `frontend/src/features/event-insight/components/event-insight-shell.tsx`
- Create: `frontend/src/features/event-insight/components/event-list-workspace.tsx`
- Create: `frontend/src/features/event-insight/components/topic-trace-workspace.tsx`
- Create: `frontend/src/features/event-insight/components/event-graph-workspace.tsx`
- Create: `frontend/src/features/event-insight/__tests__/event-insight-workspaces.test.tsx`

- [ ] **Step 1: Write failing component tests**

Cover:

```tsx
expect(screen.getByRole("heading", { name: "事件列表" })).toBeInTheDocument();
expect(screen.getByText("HBM4 量产节奏提前，先进封装产能继续吃紧")).toBeInTheDocument();
expect(screen.getByRole("heading", { name: "主题溯源" })).toBeInTheDocument();
expect(screen.getByText("阶段 03：HBM4 提前放量")).toBeInTheDocument();
expect(screen.getByRole("heading", { name: "事件关系图" })).toBeInTheDocument();
expect(screen.getByLabelText("事件关系图画布")).toBeInTheDocument();
```

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
cmd /c npm --prefix frontend run test -- src/features/event-insight/__tests__/event-insight-workspaces.test.tsx --run
```

Expected: FAIL because the event-insight components do not exist.

- [ ] **Step 3: Implement deterministic Mock workspaces**

Use Mock data only. Use Heroicons for action icons. Keep each workspace focused and split repeated UI into the shell component.

- [ ] **Step 4: Run focused tests and verify pass**

Run the Task 2 command. Expected: PASS.

### Task 3: Add Mock LLM Settings Workspace

**Files:**

- Modify: `frontend/src/pages/settings-page.tsx`
- Create: `frontend/src/features/settings/components/llm-settings-workspace.tsx`
- Modify: `frontend/src/features/settings/__tests__/settings-page.test.tsx`

- [ ] **Step 1: Write failing settings test**

Cover:

```tsx
expect(await screen.findByRole("heading", { name: "大模型配置" })).toBeInTheDocument();
expect(screen.getByText("主分析模型")).toBeInTheDocument();
expect(screen.getByText("任务默认模型")).toBeInTheDocument();
expect(screen.getByRole("button", { name: "测试连接" })).toBeDisabled();
expect(screen.getByRole("button", { name: "保存配置" })).toBeDisabled();
```

- [ ] **Step 2: Run focused test and verify failure**

```powershell
cmd /c npm --prefix frontend run test -- src/features/settings/__tests__/settings-page.test.tsx --run
```

Expected: FAIL because the Settings route still has no page body.

- [ ] **Step 3: Implement display-only settings page**

Render the approved layout and mark unavailable actions as disabled with explanatory text. Do not persist or expose API keys.

- [ ] **Step 4: Run focused test and verify pass**

Run the Task 3 command. Expected: PASS.

### Task 4: Document And Verify Increment I1

**Files:**

- Modify: `CHANGELOG.md`

- [ ] **Step 1: Record the visible increment**

Add one `Added` entry stating that Event Outlook now exposes three Mock research pages and Settings exposes the display-only LLM configuration page.

- [ ] **Step 2: Run full frontend verification**

```powershell
cmd /c npm --prefix frontend run test -- --run
cmd /c npm --prefix frontend run build
```

Expected: all frontend tests pass and Vite build succeeds.

- [ ] **Step 3: Run static calendar backend regression**

```powershell
uv run python -m pytest tests/test_event_outlook_timeline.py -q
```

Expected: existing Event Outlook backend regression passes.

- [ ] **Step 4: Manual route verification**

Open:

```text
/event-outlook?tab=domestic
/event-outlook?tab=international
/event-outlook?tab=events
/event-outlook?tab=topic-trace
/event-outlook?tab=event-graph
/settings
```

Verify that the first two routes render the original timeline and the remaining routes render the four approved Mock pages.

- [ ] **Step 5: Commit the isolated increment**

```text
feat: add event insight frontend workbenches
```

## 3. Stop Condition

I1 ends with visible Mock pages only. Do not create event-insight SQLite tables, HTTP endpoints, LLM calls, or graph dependencies in this increment.
