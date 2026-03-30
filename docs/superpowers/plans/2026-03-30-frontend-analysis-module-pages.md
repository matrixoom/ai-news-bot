# Frontend Analysis Module Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current placeholder routes with production-style `News`, `Macro`, `Market`, and `Events` module pages in the new React SPA.

**Architecture:** Reuse the app shell and route skeleton from the first slice, and implement one consistent `raw payload -> adapter -> TanStack Query hook -> route page` pipeline for each module. Each page should support URL-driven tabs, loading/error/empty states, and calm workbench-style layouts that match the approved frontend design spec.

**Tech Stack:** Vite, React, TypeScript, Tailwind CSS, React Router, TanStack Query, Vitest, Testing Library, FastAPI JSON module APIs

---

## Scope Note

This plan intentionally covers only the four read-heavy analysis modules:

- `News`
- `Macro`
- `Market`
- `Events`

It does **not** include:

- `Push Center`
- `Settings`
- shadcn/ui rollout
- ECharts integration beyond what is strictly needed for these pages

Those should stay in the next independent plan so this slice remains testable and easy to review.

## File Structure

### Shared page primitives

- `frontend/src/shared/lib/module-tabs.ts`
  - URL tab parsing and fallback helpers
- `frontend/src/shared/ui/module-tab-bar.tsx`
  - shared tab switcher for module pages
- `frontend/src/shared/ui/module-page-frame.tsx`
  - common page body layout with overview rail + side rail slots
- `frontend/src/shared/ui/panel-state.tsx`
  - reusable loading, empty, and error panels
- `frontend/src/shared/ui/last-updated-badge.tsx`
  - compact generated-at badge

### News module

- `frontend/src/pages/news-page.tsx`
  - route page for `/news`
- `frontend/src/features/news/api/get-news-module.ts`
  - fetch `/api/frontend/modules/news`
- `frontend/src/features/news/model/news-module.types.ts`
  - raw payload and view model types
- `frontend/src/features/news/model/news-module-adapter.ts`
  - normalize news sections, upstream status, and tabs
- `frontend/src/features/news/hooks/use-news-module-query.ts`
  - query hook
- `frontend/src/features/news/components/news-channel-card.tsx`
  - summary card per channel
- `frontend/src/features/news/components/news-feed-list.tsx`
  - grouped list of ranked items
- `frontend/src/features/news/components/news-status-panel.tsx`
  - side rail with source mode and upstream health
- `frontend/src/features/news/__tests__/news-page.test.tsx`
  - page-level render and tab behavior

### Macro module

- `frontend/src/pages/macro-page.tsx`
  - route page for `/macro`
- `frontend/src/features/macro/api/get-macro-module.ts`
  - fetch `/api/frontend/modules/macro`
- `frontend/src/features/macro/model/macro-module.types.ts`
  - raw payload and view model types
- `frontend/src/features/macro/model/macro-module-adapter.ts`
  - normalize macro comparison sections
- `frontend/src/features/macro/hooks/use-macro-module-query.ts`
  - query hook
- `frontend/src/features/macro/components/macro-comparison-card.tsx`
  - per-pair comparison block
- `frontend/src/features/macro/components/macro-sources-panel.tsx`
  - source and indicator summary side panel
- `frontend/src/features/macro/__tests__/macro-page.test.tsx`
  - page-level render and tab behavior

### Market module

- `frontend/src/pages/market-page.tsx`
  - route page for `/market`
- `frontend/src/features/market/api/get-market-module.ts`
  - fetch `/api/frontend/modules/market`
- `frontend/src/features/market/model/market-module.types.ts`
  - raw payload and view model types
- `frontend/src/features/market/model/market-module-adapter.ts`
  - normalize signal cards and watchlist summaries
- `frontend/src/features/market/hooks/use-market-module-query.ts`
  - query hook
- `frontend/src/features/market/components/market-signal-card.tsx`
  - model signal card
- `frontend/src/features/market/components/market-watch-panel.tsx`
  - side panel for signal counts and watch items
- `frontend/src/features/market/__tests__/market-page.test.tsx`
  - page-level render and tab behavior

### Events module

- `frontend/src/pages/events-page.tsx`
  - route page for `/events`
- `frontend/src/features/events/api/get-events-module.ts`
  - fetch `/api/frontend/modules/events`
- `frontend/src/features/events/model/events-module.types.ts`
  - raw payload and view model types
- `frontend/src/features/events/model/events-module-adapter.ts`
  - normalize time windows and official links
- `frontend/src/features/events/hooks/use-events-module-query.ts`
  - query hook
- `frontend/src/features/events/components/event-window-card.tsx`
  - timeline/time-window card
- `frontend/src/features/events/components/events-links-panel.tsx`
  - official link and watch summary panel
- `frontend/src/features/events/__tests__/events-page.test.tsx`
  - page-level render and tab behavior

### Routing and integration

- `frontend/src/app/routes.tsx`
  - switch placeholder routes to real pages
- `frontend/src/app/__tests__/router-shell.test.tsx`
  - assert the shell renders real module routes

---

### Task 1: Add shared module-page primitives and URL tab support

**Files:**
- Create: `frontend/src/shared/lib/module-tabs.ts`
- Create: `frontend/src/shared/ui/module-tab-bar.tsx`
- Create: `frontend/src/shared/ui/module-page-frame.tsx`
- Create: `frontend/src/shared/ui/panel-state.tsx`
- Create: `frontend/src/shared/ui/last-updated-badge.tsx`
- Modify: `frontend/src/app/__tests__/router-shell.test.tsx`

- [ ] **Step 1: Write failing tests for URL tab fallback and shared route rendering**

```tsx
// frontend/src/app/__tests__/router-shell.test.tsx
it("keeps module tab state in the URL", async () => {
  window.history.pushState({}, "", "/news?tab=channels");
  renderApp();
  expect(await screen.findByRole("tab", { name: "Channels" })).toHaveAttribute("aria-selected", "true");
});

it("falls back to overview when the tab query is unknown", async () => {
  window.history.pushState({}, "", "/macro?tab=nope");
  renderApp();
  expect(await screen.findByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
});
```

- [ ] **Step 2: Run the route test and verify it fails because module pages still use placeholders**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/app/__tests__/router-shell.test.tsx
```

Expected:

- FAIL because `/news` and `/macro` do not render tab controls yet

- [ ] **Step 3: Add the shared tab and panel primitives with minimal focused APIs**

```ts
// frontend/src/shared/lib/module-tabs.ts
export function resolveModuleTab(searchParams: URLSearchParams, allowedTabs: string[], fallbackTab: string) {
  const requestedTab = searchParams.get("tab");
  return requestedTab && allowedTabs.includes(requestedTab) ? requestedTab : fallbackTab;
}
```

```tsx
// frontend/src/shared/ui/module-tab-bar.tsx
export function ModuleTabBar({ tabs, activeTab, onTabChange }: ModuleTabBarProps) {
  return (
    <div role="tablist" className="flex flex-wrap gap-2">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          role="tab"
          aria-selected={tab.value === activeTab}
          onClick={() => onTabChange(tab.value)}
          className={tab.value === activeTab ? "bg-slate-900 text-white" : "bg-slate-200 text-slate-700"}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
```

```tsx
// frontend/src/shared/ui/panel-state.tsx
export function LoadingPanel({ label }: { label: string }) {
  return <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-500">{label}</div>;
}

export function ErrorPanel({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-3xl border border-red-200 bg-red-50 p-6">
      <h3 className="text-sm font-semibold text-red-900">{title}</h3>
      <p className="mt-2 text-sm text-red-700">{detail}</p>
    </div>
  );
}
```

- [ ] **Step 4: Re-run the shared route test after Task 2 starts wiring the first real module page**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/app/__tests__/router-shell.test.tsx
```

Expected:

- still partially failing until `NewsPage` is mounted in Task 2

- [ ] **Step 5: Commit the shared primitives once at least one real route consumes them**

```bash
git add frontend/src/shared/lib/module-tabs.ts frontend/src/shared/ui/module-tab-bar.tsx frontend/src/shared/ui/module-page-frame.tsx frontend/src/shared/ui/panel-state.tsx frontend/src/shared/ui/last-updated-badge.tsx frontend/src/app/__tests__/router-shell.test.tsx
git commit -m "feat(frontend): add shared module page primitives"
```

### Task 2: Implement the News module page

**Files:**
- Create: `frontend/src/pages/news-page.tsx`
- Create: `frontend/src/features/news/api/get-news-module.ts`
- Create: `frontend/src/features/news/model/news-module.types.ts`
- Create: `frontend/src/features/news/model/news-module-adapter.ts`
- Create: `frontend/src/features/news/hooks/use-news-module-query.ts`
- Create: `frontend/src/features/news/components/news-channel-card.tsx`
- Create: `frontend/src/features/news/components/news-feed-list.tsx`
- Create: `frontend/src/features/news/components/news-status-panel.tsx`
- Create: `frontend/src/features/news/__tests__/news-page.test.tsx`
- Modify: `frontend/src/app/routes.tsx`
- Modify: `frontend/src/app/__tests__/router-shell.test.tsx`

- [ ] **Step 1: Write the failing News page test**

```tsx
// frontend/src/features/news/__tests__/news-page.test.tsx
it("renders channel summaries, ranked headlines, and upstream status", async () => {
  server.use(http.get("/api/frontend/modules/news", () => HttpResponse.json(mockNewsModulePayload)));
  window.history.pushState({}, "", "/news?tab=channels");
  renderApp();

  expect(await screen.findByRole("heading", { name: "Tech News" })).toBeInTheDocument();
  expect(screen.getByText("Upstream")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Headline 1" })).toHaveAttribute("href", "https://example.com/1");
});
```

- [ ] **Step 2: Run the News test and verify it fails**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/features/news/__tests__/news-page.test.tsx
```

Expected:

- FAIL because the news feature files and route page do not exist yet

- [ ] **Step 3: Implement the raw payload, adapter, hook, and page composition**

```ts
// frontend/src/features/news/model/news-module.types.ts
export interface NewsModulePayload {
  generated_at: string;
  news_mode: string;
  news_mode_options: Array<{ value: string; label: string }>;
  upstream_service_status: { status: string; healthy: boolean; detail: string };
  module: {
    id: "news";
    status: string;
    loading: boolean;
    details: Array<{
      id: string;
      label: string;
      note: string;
      section: {
        key: string;
        title: string;
        status: string;
        description: string;
        item_count: number;
        items: Array<{ rank: number; title: string; source: string; url: string; published_at: string; tag: string; summary: string }>;
      };
    }>;
  };
}
```

```tsx
// frontend/src/pages/news-page.tsx
export function NewsPage() {
  const { activeTab, setActiveTab } = useModuleTabs(["overview", "channels", "sources", "brief"], "overview");
  const query = useNewsModuleQuery();

  if (query.isLoading) return <LoadingPanel label="Loading news workbench..." />;
  if (query.isError) return <ErrorPanel title="News module unavailable" detail="Please retry in a moment." />;

  return (
    <ModulePageFrame
      title="News"
      subtitle="Intelligence workbench"
      toolbar={<ModuleTabBar tabs={NEWS_TABS} activeTab={activeTab} onTabChange={setActiveTab} />}
      side={<NewsStatusPanel model={query.data} />}
    >
      <NewsFeedList model={query.data} activeTab={activeTab} />
    </ModulePageFrame>
  );
}
```

- [ ] **Step 4: Re-run the News and shell tests**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/features/news/__tests__/news-page.test.tsx
cmd /c npm --prefix frontend run test -- --run src/app/__tests__/router-shell.test.tsx
```

Expected:

- PASS for both tests

- [ ] **Step 5: Commit the News page slice**

```bash
git add frontend/src/pages/news-page.tsx frontend/src/features/news frontend/src/app/routes.tsx frontend/src/app/__tests__/router-shell.test.tsx
git commit -m "feat(frontend): add news module page"
```

### Task 3: Implement the Macro module page

**Files:**
- Create: `frontend/src/pages/macro-page.tsx`
- Create: `frontend/src/features/macro/api/get-macro-module.ts`
- Create: `frontend/src/features/macro/model/macro-module.types.ts`
- Create: `frontend/src/features/macro/model/macro-module-adapter.ts`
- Create: `frontend/src/features/macro/hooks/use-macro-module-query.ts`
- Create: `frontend/src/features/macro/components/macro-comparison-card.tsx`
- Create: `frontend/src/features/macro/components/macro-sources-panel.tsx`
- Create: `frontend/src/features/macro/__tests__/macro-page.test.tsx`
- Modify: `frontend/src/app/routes.tsx`

- [ ] **Step 1: Write the failing Macro page test**

```tsx
it("renders comparison cards, delta summaries, and source lists", async () => {
  server.use(http.get("/api/frontend/modules/macro", () => HttpResponse.json(mockMacroModulePayload)));
  window.history.pushState({}, "", "/macro?tab=compare");
  renderApp();

  expect(await screen.findByRole("heading", { name: "Inflation vs Growth" })).toBeInTheDocument();
  expect(screen.getByText("CPI: 0.3%")).toBeInTheDocument();
  expect(screen.getByText("National Bureau of Statistics")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the Macro test and verify it fails**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/features/macro/__tests__/macro-page.test.tsx
```

Expected:

- FAIL because the macro route still resolves to a placeholder

- [ ] **Step 3: Implement the Macro page with comparison-focused sections**

```tsx
// frontend/src/pages/macro-page.tsx
export function MacroPage() {
  const { activeTab, setActiveTab } = useModuleTabs(["overview", "compare", "indicators", "sources"], "overview");
  const query = useMacroModuleQuery();

  if (query.isLoading) return <LoadingPanel label="Loading macro comparisons..." />;
  if (query.isError) return <ErrorPanel title="Macro module unavailable" detail="The comparison payload could not be loaded." />;

  return (
    <ModulePageFrame
      title="Macro"
      subtitle="Indicators and comparisons"
      toolbar={<ModuleTabBar tabs={MACRO_TABS} activeTab={activeTab} onTabChange={setActiveTab} />}
      side={<MacroSourcesPanel model={query.data} activeTab={activeTab} />}
    >
      <section className="grid gap-4">
        {query.data.sections.map((section) => (
          <MacroComparisonCard key={section.key} section={section} activeTab={activeTab} />
        ))}
      </section>
    </ModulePageFrame>
  );
}
```

- [ ] **Step 4: Re-run the Macro test**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/features/macro/__tests__/macro-page.test.tsx
```

Expected:

- PASS

- [ ] **Step 5: Commit the Macro page slice**

```bash
git add frontend/src/pages/macro-page.tsx frontend/src/features/macro frontend/src/app/routes.tsx
git commit -m "feat(frontend): add macro module page"
```

### Task 4: Implement the Market module page

**Files:**
- Create: `frontend/src/pages/market-page.tsx`
- Create: `frontend/src/features/market/api/get-market-module.ts`
- Create: `frontend/src/features/market/model/market-module.types.ts`
- Create: `frontend/src/features/market/model/market-module-adapter.ts`
- Create: `frontend/src/features/market/hooks/use-market-module-query.ts`
- Create: `frontend/src/features/market/components/market-signal-card.tsx`
- Create: `frontend/src/features/market/components/market-watch-panel.tsx`
- Create: `frontend/src/features/market/__tests__/market-page.test.tsx`
- Modify: `frontend/src/app/routes.tsx`

- [ ] **Step 1: Write the failing Market page test**

```tsx
it("renders signal cards and watch summaries", async () => {
  server.use(http.get("/api/frontend/modules/market", () => HttpResponse.json(mockMarketModulePayload)));
  window.history.pushState({}, "", "/market?tab=signals");
  renderApp();

  expect(await screen.findByRole("heading", { name: "CSI 300" })).toBeInTheDocument();
  expect(screen.getByText("neutral")).toBeInTheDocument();
  expect(screen.getByText("Watchlist")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the Market test and verify it fails**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/features/market/__tests__/market-page.test.tsx
```

Expected:

- FAIL because the market route still uses a placeholder page

- [ ] **Step 3: Implement the Market page with signal-first cards**

```tsx
// frontend/src/pages/market-page.tsx
export function MarketPage() {
  const { activeTab, setActiveTab } = useModuleTabs(["overview", "signals", "models", "watchlist"], "overview");
  const query = useMarketModuleQuery();

  if (query.isLoading) return <LoadingPanel label="Loading market models..." />;
  if (query.isError) return <ErrorPanel title="Market module unavailable" detail="The market signal payload could not be loaded." />;

  return (
    <ModulePageFrame
      title="Market"
      subtitle="Signals and watchlists"
      toolbar={<ModuleTabBar tabs={MARKET_TABS} activeTab={activeTab} onTabChange={setActiveTab} />}
      side={<MarketWatchPanel model={query.data} activeTab={activeTab} />}
    >
      <div className="grid gap-4 md:grid-cols-2">
        {query.data.cards.map((card) => (
          <MarketSignalCard key={card.key} card={card} />
        ))}
      </div>
    </ModulePageFrame>
  );
}
```

- [ ] **Step 4: Re-run the Market test**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/features/market/__tests__/market-page.test.tsx
```

Expected:

- PASS

- [ ] **Step 5: Commit the Market page slice**

```bash
git add frontend/src/pages/market-page.tsx frontend/src/features/market frontend/src/app/routes.tsx
git commit -m "feat(frontend): add market module page"
```

### Task 5: Implement the Events module page

**Files:**
- Create: `frontend/src/pages/events-page.tsx`
- Create: `frontend/src/features/events/api/get-events-module.ts`
- Create: `frontend/src/features/events/model/events-module.types.ts`
- Create: `frontend/src/features/events/model/events-module-adapter.ts`
- Create: `frontend/src/features/events/hooks/use-events-module-query.ts`
- Create: `frontend/src/features/events/components/event-window-card.tsx`
- Create: `frontend/src/features/events/components/events-links-panel.tsx`
- Create: `frontend/src/features/events/__tests__/events-page.test.tsx`
- Modify: `frontend/src/app/routes.tsx`

- [ ] **Step 1: Write the failing Events page test**

```tsx
it("renders time windows, official links, and watch summaries", async () => {
  server.use(http.get("/api/frontend/modules/events", () => HttpResponse.json(mockEventsModulePayload)));
  window.history.pushState({}, "", "/events?tab=timeline");
  renderApp();

  expect(await screen.findByRole("heading", { name: "Next 7 Days" })).toBeInTheDocument();
  expect(screen.getByText("National Bureau of Statistics release window")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Federal Reserve Calendar" })).toHaveAttribute("href", expect.stringContaining("federalreserve"));
});
```

- [ ] **Step 2: Run the Events test and verify it fails**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/features/events/__tests__/events-page.test.tsx
```

Expected:

- FAIL because the events route has not been implemented

- [ ] **Step 3: Implement the Events page with timeline and source views**

```tsx
// frontend/src/pages/events-page.tsx
export function EventsPage() {
  const { activeTab, setActiveTab } = useModuleTabs(["timeline", "calendar", "watch", "sources"], "timeline");
  const query = useEventsModuleQuery();

  if (query.isLoading) return <LoadingPanel label="Loading event windows..." />;
  if (query.isError) return <ErrorPanel title="Events module unavailable" detail="The event timeline payload could not be loaded." />;

  return (
    <ModulePageFrame
      title="Events"
      subtitle="Timeline and watch windows"
      toolbar={<ModuleTabBar tabs={EVENTS_TABS} activeTab={activeTab} onTabChange={setActiveTab} />}
      side={<EventsLinksPanel model={query.data} activeTab={activeTab} />}
    >
      <div className="grid gap-4">
        {query.data.windows.map((windowSection) => (
          <EventWindowCard key={windowSection.key} section={windowSection} activeTab={activeTab} />
        ))}
      </div>
    </ModulePageFrame>
  );
}
```

- [ ] **Step 4: Re-run the Events test**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/features/events/__tests__/events-page.test.tsx
```

Expected:

- PASS

- [ ] **Step 5: Commit the Events page slice**

```bash
git add frontend/src/pages/events-page.tsx frontend/src/features/events frontend/src/app/routes.tsx
git commit -m "feat(frontend): add events module page"
```

### Task 6: Verify the four-module slice end to end

**Files:**
- Modify: `frontend/src/app/routes.tsx`
- Modify: `frontend/src/app/__tests__/router-shell.test.tsx`

- [ ] **Step 1: Run the focused frontend test set**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/app/__tests__/router-shell.test.tsx
cmd /c npm --prefix frontend run test -- --run src/features/news/__tests__/news-page.test.tsx
cmd /c npm --prefix frontend run test -- --run src/features/macro/__tests__/macro-page.test.tsx
cmd /c npm --prefix frontend run test -- --run src/features/market/__tests__/market-page.test.tsx
cmd /c npm --prefix frontend run test -- --run src/features/events/__tests__/events-page.test.tsx
```

Expected:

- all route and module page tests PASS

- [ ] **Step 2: Run the full frontend and backend verification set**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run
cmd /c npm --prefix frontend run build
uv run python -m pytest tests/test_task11_frontend_spa_serving.py tests/test_task03_web_app_shell.py -q
```

Expected:

- all frontend tests pass
- frontend production build succeeds
- existing backend SPA-serving regressions still pass unchanged

- [ ] **Step 3: Manually confirm the new module routes**

Run:

```powershell
uv run python main.py web --host 127.0.0.1 --port 8000 --no-reload
```

Manual checks:

- `http://127.0.0.1:8000/news` renders tabbed channel summaries and headline lists
- `http://127.0.0.1:8000/macro` renders comparison sections and source panels
- `http://127.0.0.1:8000/market` renders signal cards and watch summaries
- `http://127.0.0.1:8000/events` renders time-window cards and official links

- [ ] **Step 4: Commit the route-integration finish line**

```bash
git add frontend/src/app/routes.tsx frontend/src/app/__tests__/router-shell.test.tsx frontend/src/pages frontend/src/features/news frontend/src/features/macro frontend/src/features/market frontend/src/features/events
git commit -m "feat(frontend): add analysis module pages"
```

- [ ] **Step 5: Record the next planning boundary**

Add this note to the implementation handoff or PR description:

```text
This slice intentionally stops after the four read-heavy analysis module pages. The next plan should cover Push Center, Settings, and any remaining migration hardening such as theme persistence, shared data-table primitives, and future ECharts upgrades.
```

## Self-Review

### Spec coverage

- `News`, `Macro`, `Market`, and `Events` independent module pages: covered in Tasks 2-5
- URL-driven secondary views via tabs and query params: covered in Task 1 and consumed in Tasks 2-5
- Calm workbench layout with header/body/side rail composition: covered in Task 1 and reused throughout
- Separation between backend payloads and page components: covered by per-module `types + adapter + hook` stacks in Tasks 2-5
- Push Center and Settings exclusion: explicitly deferred in Scope Note and Task 6 handoff

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” instructions appear in the tasks
- Each task names concrete files, tests, commands, and commit boundaries
- Verification steps explicitly list the test commands and manual route checks

### Type consistency

- Every module follows the same `get-* -> types -> adapter -> hook -> page` chain
- Tab values in the tests match the tab lists used in each page
- Route ownership stays in `frontend/src/app/routes.tsx`, while page rendering stays in `frontend/src/pages/*`
