# Frontend Shell and Dashboard Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first shippable slice of the new frontend by introducing a standalone React/Vite SPA, a reusable app shell, and a production-style Dashboard page wired to the existing FastAPI backend.

**Architecture:** Add a new `frontend/` SPA that owns routing, layout, and dashboard presentation while FastAPI continues to provide JSON APIs. The backend will conditionally serve the built SPA for workbench routes when `frontend/dist` exists, while preserving the legacy shell as a fallback during migration.

**Tech Stack:** Vite, React, TypeScript, Tailwind CSS, React Router, TanStack Query, Zustand, Vitest, Testing Library, FastAPI, pytest

---

## Scope Note

The approved design spec covers several semi-independent subsystems:

- frontend shell and routing
- dashboard homepage
- analysis module pages
- push center
- settings
- migration/hardening

This plan intentionally covers the first independently shippable slice:

- scaffold the new SPA
- introduce the app shell and top-level routes
- implement the Dashboard homepage
- wire the FastAPI app to serve the compiled SPA

After this plan lands, write follow-on implementation plans for:

- `News + Macro + Market + Events` module pages
- `Push Center + Settings`
- migration hardening and platformization follow-up

## File Structure

### New frontend workspace

- `frontend/package.json`
  - npm scripts and frontend dependencies
- `frontend/tsconfig.json`
  - TypeScript compiler settings for browser code
- `frontend/tsconfig.node.json`
  - TypeScript settings for Vite config files
- `frontend/vite.config.ts`
  - Vite build/test configuration
- `frontend/postcss.config.js`
  - Tailwind PostCSS integration
- `frontend/tailwind.config.ts`
  - Tailwind content scan and theme extension
- `frontend/index.html`
  - Vite HTML entry
- `frontend/src/index.css`
  - Tailwind imports plus global visual tokens
- `frontend/src/main.tsx`
  - React bootstrap
- `frontend/src/test/setup.ts`
  - Vitest + Testing Library setup

### App shell and routing

- `frontend/src/app/app.tsx`
  - top-level app entry
- `frontend/src/app/providers.tsx`
  - Query client and global providers
- `frontend/src/app/routes.tsx`
  - top-level route table
- `frontend/src/shared/lib/cn.ts`
  - className merge helper
- `frontend/src/shared/config/nav-items.ts`
  - shared navigation metadata
- `frontend/src/shared/types/page-meta.ts`
  - page metadata type used by shell
- `frontend/src/layouts/app-shell.tsx`
  - sidebar + header + outlet layout
- `frontend/src/layouts/sidebar-nav.tsx`
  - primary sidebar navigation
- `frontend/src/layouts/header-bar.tsx`
  - page title / description / top controls
- `frontend/src/pages/dashboard-page.tsx`
  - dashboard route page
- `frontend/src/pages/module-placeholder-page.tsx`
  - placeholder page for routes not yet implemented

### Dashboard feature

- `frontend/src/features/dashboard/api/get-dashboard.ts`
  - fetch raw dashboard payload
- `frontend/src/features/dashboard/model/dashboard.types.ts`
  - raw API and view model TypeScript types
- `frontend/src/features/dashboard/model/dashboard-adapter.ts`
  - convert raw API payload into dashboard view model
- `frontend/src/features/dashboard/hooks/use-dashboard-query.ts`
  - TanStack Query hook
- `frontend/src/features/dashboard/components/stat-card.tsx`
  - KPI strip card
- `frontend/src/features/dashboard/components/brief-card.tsx`
  - summary/brief card
- `frontend/src/features/dashboard/components/module-snapshot-card.tsx`
  - module snapshot card
- `frontend/src/features/dashboard/components/dashboard-skeleton.tsx`
  - dashboard loading state

### Frontend tests

- `frontend/src/app/__tests__/bootstrap.test.tsx`
  - frontend bootstrap smoke test
- `frontend/src/app/__tests__/router-shell.test.tsx`
  - app shell and route smoke test
- `frontend/src/features/dashboard/__tests__/dashboard-page.test.tsx`
  - dashboard render test against mocked payload

### Backend SPA serving

- `src/app/web/spa_assets.py`
  - helper functions for SPA route serving
- `tests/test_task11_frontend_spa_serving.py`
  - backend SPA serving regression tests
- `src/app/web/fastapi_app.py`
  - FastAPI integration for new SPA routes

### Docs and repo hygiene

- `.gitignore`
  - ignore frontend build/runtime artifacts
- `README.md`
  - frontend development commands
- `README.zh.md`
  - Chinese frontend development commands

---

### Task 1: Bootstrap the standalone frontend workspace

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/index.css`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app/app.tsx`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/app/__tests__/bootstrap.test.tsx`
- Modify: `.gitignore`

- [ ] **Step 1: Create the package manifest, test harness, and a failing bootstrap test**

```json
// frontend/package.json
{
  "name": "ai-news-bot-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.66.8",
    "echarts": "^5.6.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.30.1",
    "zustand": "^5.0.3"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.2.0",
    "@testing-library/user-event": "^14.6.1",
    "@types/node": "^22.13.10",
    "@types/react": "^18.3.18",
    "@types/react-dom": "^18.3.5",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "jsdom": "^26.0.0",
    "postcss": "^8.5.3",
    "tailwindcss": "^3.4.17",
    "typescript": "^5.8.2",
    "vite": "^6.2.1",
    "vitest": "^3.0.8"
  }
}
```

```json
// frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

```json
// frontend/tsconfig.node.json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts", "tailwind.config.ts"]
}
```

```ts
// frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
```

```js
// frontend/postcss.config.js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

```ts
// frontend/tailwind.config.ts
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
} satisfies Config;
```

```ts
// frontend/src/test/setup.ts
import "@testing-library/jest-dom/vitest";
```

```tsx
// frontend/src/app/__tests__/bootstrap.test.tsx
import { render, screen } from "@testing-library/react";
import { App } from "../app";

describe("App bootstrap", () => {
  it("renders the initial frontend title", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "AI News Bot" })).toBeInTheDocument();
    expect(screen.getByText("Loading workspace...")).toBeInTheDocument();
  });
});
```

```gitignore
# .gitignore
frontend/node_modules/
frontend/dist/
```

- [ ] **Step 2: Install dependencies and run the bootstrap test to verify it fails**

Run:

```powershell
cmd /c npm --prefix frontend install
cmd /c npm --prefix frontend run test -- --run src/app/__tests__/bootstrap.test.tsx
```

Expected:

- `npm install` creates `frontend/package-lock.json`
- Vitest fails with a module resolution error for `frontend/src/app/app.tsx`

- [ ] **Step 3: Add the minimal Vite entrypoint, styles, and App component**

```html
<!-- frontend/index.html -->
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI News Bot</title>
  </head>
  <body class="bg-slate-950">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

```css
/* frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  color-scheme: light;
}

body {
  margin: 0;
  min-height: 100vh;
  font-family: Inter, "Segoe UI", sans-serif;
  background: #f4f7fb;
  color: #0f172a;
}
```

```tsx
// frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/app";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

```tsx
// frontend/src/app/app.tsx
export function App() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100">
      <section className="rounded-2xl border border-slate-200 bg-white px-8 py-10 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">AI News Bot</h1>
        <p className="mt-3 text-sm text-slate-600">Loading workspace...</p>
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Re-run the bootstrap test and the frontend build**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/app/__tests__/bootstrap.test.tsx
cmd /c npm --prefix frontend run build
```

Expected:

- Vitest reports `1 passed`
- Vite writes a production build under `frontend/dist`

- [ ] **Step 5: Commit the bootstrap workspace**

```bash
git add .gitignore frontend
git commit -m "feat: scaffold frontend workspace"
```

### Task 2: Build the reusable app shell and top-level route skeleton

**Files:**
- Create: `frontend/src/app/providers.tsx`
- Create: `frontend/src/app/routes.tsx`
- Create: `frontend/src/shared/lib/cn.ts`
- Create: `frontend/src/shared/types/page-meta.ts`
- Create: `frontend/src/shared/config/nav-items.ts`
- Create: `frontend/src/layouts/app-shell.tsx`
- Create: `frontend/src/layouts/sidebar-nav.tsx`
- Create: `frontend/src/layouts/header-bar.tsx`
- Create: `frontend/src/pages/module-placeholder-page.tsx`
- Modify: `frontend/src/app/app.tsx`
- Create: `frontend/src/app/__tests__/router-shell.test.tsx`

- [ ] **Step 1: Add a failing route-shell test**

```tsx
// frontend/src/app/__tests__/router-shell.test.tsx
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "../providers";
import { appRoutes } from "../routes";

describe("Workbench shell", () => {
  it("renders the sidebar and the active route title", async () => {
    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/news"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Push Center" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "News" })).toBeInTheDocument();
    expect(screen.getByText("Module page coming in the next slice.")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the route-shell test to verify it fails**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/app/__tests__/router-shell.test.tsx
```

Expected:

- Vitest fails because `providers.tsx` and `routes.tsx` do not exist yet

- [ ] **Step 3: Implement providers, route metadata, shell layout, and placeholder pages**

```ts
// frontend/src/shared/types/page-meta.ts
export type PageMeta = {
  title: string;
  description: string;
};
```

```ts
// frontend/src/shared/config/nav-items.ts
import type { PageMeta } from "../types/page-meta";

export type NavItem = PageMeta & {
  to: string;
};

export const primaryNavItems: NavItem[] = [
  { to: "/dashboard", title: "Dashboard", description: "Cross-module overview" },
  { to: "/news", title: "News", description: "Intelligence workbench" },
  { to: "/macro", title: "Macro", description: "Indicators and comparisons" },
  { to: "/market", title: "Market", description: "Signals and watchlists" },
  { to: "/events", title: "Events", description: "Timeline and watch windows" },
  { to: "/push", title: "Push Center", description: "Templates and schedules" },
];

export const secondaryNavItems: NavItem[] = [
  { to: "/settings", title: "Settings", description: "Preferences and system defaults" },
];
```

```ts
// frontend/src/shared/lib/cn.ts
export function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}
```

```tsx
// frontend/src/app/providers.tsx
import { PropsWithChildren, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```

```tsx
// frontend/src/layouts/sidebar-nav.tsx
import { NavLink } from "react-router-dom";
import { primaryNavItems, secondaryNavItems } from "../shared/config/nav-items";
import { cn } from "../shared/lib/cn";

function NavSection({ items }: { items: typeof primaryNavItems }) {
  return (
    <div className="space-y-1">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            cn(
              "block rounded-xl px-3 py-2 text-sm transition",
              isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )
          }
        >
          <div className="font-medium">{item.title}</div>
          <div className="mt-1 text-xs opacity-75">{item.description}</div>
        </NavLink>
      ))}
    </div>
  );
}

export function SidebarNav() {
  return (
    <nav aria-label="Primary" className="flex h-full flex-col justify-between">
      <div>
        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Research Desk</p>
          <h1 className="mt-2 text-xl font-semibold text-slate-950">AI News Bot</h1>
        </div>
        <NavSection items={primaryNavItems} />
      </div>
      <NavSection items={secondaryNavItems} />
    </nav>
  );
}
```

```tsx
// frontend/src/layouts/header-bar.tsx
import type { PageMeta } from "../shared/types/page-meta";

export function HeaderBar({ meta }: { meta: PageMeta }) {
  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-8 py-5">
      <div>
        <h2 className="text-2xl font-semibold text-slate-950">{meta.title}</h2>
        <p className="mt-1 text-sm text-slate-500">{meta.description}</p>
      </div>
      <div className="flex items-center gap-3 text-sm text-slate-500">
        <button className="rounded-lg border border-slate-200 px-3 py-2 text-slate-700">Refresh</button>
        <span>Freshness: live</span>
      </div>
    </header>
  );
}
```

```tsx
// frontend/src/layouts/app-shell.tsx
import { Outlet, useMatches } from "react-router-dom";
import { HeaderBar } from "./header-bar";
import { SidebarNav } from "./sidebar-nav";
import type { PageMeta } from "../shared/types/page-meta";

export function AppShell() {
  const matches = useMatches();
  const leaf = matches[matches.length - 1];
  const meta = (leaf.handle as PageMeta | undefined) ?? {
    title: "Dashboard",
    description: "Cross-module overview",
  };

  return (
    <div className="grid min-h-screen grid-cols-[260px_1fr] bg-slate-100">
      <aside className="border-r border-slate-200 bg-white p-6">
        <SidebarNav />
      </aside>
      <div className="flex min-h-screen flex-col">
        <HeaderBar meta={meta} />
        <main className="flex-1 p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

```tsx
// frontend/src/pages/module-placeholder-page.tsx
export function ModulePlaceholderPage() {
  return (
    <section className="rounded-3xl border border-dashed border-slate-300 bg-white p-10 text-center shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900">Route ready</h3>
      <p className="mt-2 text-sm text-slate-500">Module page coming in the next slice.</p>
    </section>
  );
}
```

```tsx
// frontend/src/pages/dashboard-page.tsx
export function DashboardPage() {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-10 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900">Dashboard foundation</h3>
      <p className="mt-2 text-sm text-slate-500">Dashboard widgets arrive in Task 3.</p>
    </section>
  );
}
```

```tsx
// frontend/src/app/routes.tsx
import { Navigate, type RouteObject } from "react-router-dom";
import { AppShell } from "../layouts/app-shell";
import { DashboardPage } from "../pages/dashboard-page";
import { ModulePlaceholderPage } from "../pages/module-placeholder-page";

export const appRoutes: RouteObject[] = [
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: "dashboard",
        element: <DashboardPage />,
        handle: { title: "Dashboard", description: "Cross-module overview" },
      },
      {
        path: "news",
        element: <ModulePlaceholderPage />,
        handle: { title: "News", description: "Intelligence workbench" },
      },
      {
        path: "macro",
        element: <ModulePlaceholderPage />,
        handle: { title: "Macro", description: "Indicators and comparisons" },
      },
      {
        path: "market",
        element: <ModulePlaceholderPage />,
        handle: { title: "Market", description: "Signals and watchlists" },
      },
      {
        path: "events",
        element: <ModulePlaceholderPage />,
        handle: { title: "Events", description: "Timeline and watch windows" },
      },
      {
        path: "push",
        element: <ModulePlaceholderPage />,
        handle: { title: "Push Center", description: "Templates and schedules" },
      },
      {
        path: "settings",
        element: <ModulePlaceholderPage />,
        handle: { title: "Settings", description: "Preferences and system defaults" },
      },
    ],
  },
];
```

```tsx
// frontend/src/app/app.tsx
import { RouterProvider, createBrowserRouter } from "react-router-dom";
import { AppProviders } from "./providers";
import { appRoutes } from "./routes";

const router = createBrowserRouter(appRoutes);

export function App() {
  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
```

- [ ] **Step 4: Re-run the route-shell test**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/app/__tests__/router-shell.test.tsx
```

Expected:

- Vitest reports `1 passed`
- The shell renders the sidebar and the `/news` placeholder route

- [ ] **Step 5: Commit the shell and route skeleton**

```bash
git add frontend
git commit -m "feat: add frontend shell and top-level routes"
```

### Task 3: Implement the Dashboard data layer and homepage UI

**Files:**
- Create: `frontend/src/features/dashboard/model/dashboard.types.ts`
- Create: `frontend/src/features/dashboard/model/dashboard-adapter.ts`
- Create: `frontend/src/features/dashboard/api/get-dashboard.ts`
- Create: `frontend/src/features/dashboard/hooks/use-dashboard-query.ts`
- Create: `frontend/src/features/dashboard/components/stat-card.tsx`
- Create: `frontend/src/features/dashboard/components/brief-card.tsx`
- Create: `frontend/src/features/dashboard/components/module-snapshot-card.tsx`
- Create: `frontend/src/features/dashboard/components/dashboard-skeleton.tsx`
- Modify: `frontend/src/pages/dashboard-page.tsx`
- Create: `frontend/src/features/dashboard/__tests__/dashboard-page.test.tsx`

- [ ] **Step 1: Add a failing dashboard page test against a mocked API response**

```tsx
// frontend/src/features/dashboard/__tests__/dashboard-page.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { DashboardPage } from "../../../pages/dashboard-page";
import { vi } from "vitest";

const dashboardPayload = {
  generated_at: "2026-03-30T08:00:00Z",
  title: "Trend Insights",
  subtitle: "Asia session opened stronger while policy headlines stayed mixed.",
  coverage_note: "3 modules are live, 1 module is degraded.",
  highlights: [
    "Technology headlines turned constructive overnight.",
    "Macro refresh completed for the China and US pairs.",
    "One data source is still in degraded mode."
  ],
  news_mode: "hybrid",
  news_sections: [
    { key: "technology", title: "Technology", status: "live", description: "Tech channel", item_count: 2, items: [] }
  ],
  macro_sections: [
    { key: "rates", title: "Rates Spread", status: "live", summary: "China 10Y minus US 10Y" }
  ],
  market_sections: [
    { key: "hstech", label: "HSTECH", status: "live", signal: "constructive" }
  ],
  event_sections: [
    { key: "this-week", title: "This Week", status: "live", items: [{ title: "PMI release" }] }
  ],
  data_status: [
    { key: "news", label: "News", status: "live", detail: "Hybrid sources healthy" },
    { key: "macro", label: "Macro", status: "degraded", detail: "One official source lagging" }
  ]
};

describe("DashboardPage", () => {
  it("renders KPI cards, brief items, and module snapshots from the API payload", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(dashboardPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <DashboardPage />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Trend Insights")).toBeInTheDocument();
    });

    expect(screen.getByText("Today Brief")).toBeInTheDocument();
    expect(screen.getByText("Technology headlines turned constructive overnight.")).toBeInTheDocument();
    expect(screen.getByText("News coverage")).toBeInTheDocument();
    expect(screen.getByText("Module snapshots")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open News" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the dashboard page test to verify it fails**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/features/dashboard/__tests__/dashboard-page.test.tsx
```

Expected:

- Vitest fails because the dashboard feature files and render logic do not exist yet

- [ ] **Step 3: Implement the dashboard types, adapter, query hook, components, and page**

```ts
// frontend/src/features/dashboard/model/dashboard.types.ts
export type RawDashboardPayload = {
  generated_at: string;
  title: string;
  subtitle: string;
  coverage_note: string;
  highlights: string[];
  news_sections: Array<{ key: string; title: string; status: string; item_count: number }>;
  macro_sections: Array<{ key: string; title: string; status: string; summary: string }>;
  market_sections: Array<{ key: string; label: string; status: string; signal: string }>;
  event_sections: Array<{ key: string; title: string; status: string; items: Array<{ title: string }> }>;
  data_status: Array<{ key: string; label: string; status: string; detail: string }>;
};

export type DashboardViewModel = {
  title: string;
  subtitle: string;
  generatedAtLabel: string;
  stats: Array<{ label: string; value: string; tone: "default" | "warning" }>;
  briefItems: string[];
  statusItems: Array<{ label: string; detail: string; status: string }>;
  snapshots: Array<{ title: string; description: string; href: string; actionLabel: string }>;
};
```

```ts
// frontend/src/features/dashboard/model/dashboard-adapter.ts
import type { DashboardViewModel, RawDashboardPayload } from "./dashboard.types";

export function adaptDashboard(payload: RawDashboardPayload): DashboardViewModel {
  const degradedCount = payload.data_status.filter((item) => item.status !== "live").length;

  return {
    title: payload.title,
    subtitle: payload.subtitle,
    generatedAtLabel: new Date(payload.generated_at).toLocaleString("en-US", {
      hour12: false,
    }),
    stats: [
      { label: "News coverage", value: String(payload.news_sections.reduce((sum, item) => sum + item.item_count, 0)), tone: "default" },
      { label: "Macro views", value: String(payload.macro_sections.length), tone: "default" },
      { label: "Market signals", value: String(payload.market_sections.length), tone: "default" },
      { label: "Event windows", value: String(payload.event_sections.length), tone: "default" },
      { label: "Degraded modules", value: String(degradedCount), tone: degradedCount > 0 ? "warning" : "default" },
    ],
    briefItems: payload.highlights,
    statusItems: payload.data_status.map((item) => ({
      label: item.label,
      detail: item.detail,
      status: item.status,
    })),
    snapshots: [
      {
        title: "News",
        description: payload.news_sections[0]?.title ?? "Hybrid intelligence channels",
        href: "/news",
        actionLabel: "Open News",
      },
      {
        title: "Macro",
        description: payload.macro_sections[0]?.summary ?? "Indicator comparison deck",
        href: "/macro",
        actionLabel: "Open Macro",
      },
      {
        title: "Market",
        description: payload.market_sections[0]?.signal ?? "Signal workbench",
        href: "/market",
        actionLabel: "Open Market",
      },
      {
        title: "Events",
        description: payload.event_sections[0]?.title ?? "Upcoming policy windows",
        href: "/events",
        actionLabel: "Open Events",
      },
      {
        title: "Push",
        description: "Template and schedule health",
        href: "/push",
        actionLabel: "Open Push",
      },
    ],
  };
}
```

```ts
// frontend/src/features/dashboard/api/get-dashboard.ts
import type { RawDashboardPayload } from "../model/dashboard.types";

export async function getDashboard(): Promise<RawDashboardPayload> {
  const response = await fetch("/api/frontend/dashboard", {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`dashboard request failed: ${response.status}`);
  }

  return response.json() as Promise<RawDashboardPayload>;
}
```

```ts
// frontend/src/features/dashboard/hooks/use-dashboard-query.ts
import { useQuery } from "@tanstack/react-query";
import { getDashboard } from "../api/get-dashboard";
import { adaptDashboard } from "../model/dashboard-adapter";

export function useDashboardQuery() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => adaptDashboard(await getDashboard()),
    staleTime: 60_000,
  });
}
```

```tsx
// frontend/src/features/dashboard/components/stat-card.tsx
type StatCardProps = {
  label: string;
  value: string;
  tone?: "default" | "warning";
};

export function StatCard({ label, value, tone = "default" }: StatCardProps) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={tone === "warning" ? "mt-3 text-2xl font-semibold text-amber-600" : "mt-3 text-2xl font-semibold text-slate-900"}>
        {value}
      </p>
    </article>
  );
}
```

```tsx
// frontend/src/features/dashboard/components/brief-card.tsx
type BriefCardProps = {
  title: string;
  items: string[];
};

export function BriefCard({ title, items }: BriefCardProps) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
      <ul className="mt-4 space-y-3 text-sm text-slate-600">
        {items.map((item) => (
          <li key={item} className="rounded-xl bg-slate-50 px-4 py-3">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}
```

```tsx
// frontend/src/features/dashboard/components/module-snapshot-card.tsx
import { Link } from "react-router-dom";

type ModuleSnapshotCardProps = {
  title: string;
  description: string;
  href: string;
  actionLabel: string;
};

export function ModuleSnapshotCard({ title, description, href, actionLabel }: ModuleSnapshotCardProps) {
  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h4 className="text-base font-semibold text-slate-900">{title}</h4>
      <p className="mt-2 text-sm text-slate-500">{description}</p>
      <Link className="mt-5 inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white" to={href}>
        {actionLabel}
      </Link>
    </article>
  );
}
```

```tsx
// frontend/src/features/dashboard/components/dashboard-skeleton.tsx
export function DashboardSkeleton() {
  return (
    <section className="space-y-6" aria-label="Dashboard loading">
      <div className="h-28 animate-pulse rounded-3xl bg-slate-200" />
      <div className="grid grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="h-28 animate-pulse rounded-2xl bg-slate-200" />
        ))}
      </div>
      <div className="grid grid-cols-[2fr_1fr] gap-6">
        <div className="h-80 animate-pulse rounded-3xl bg-slate-200" />
        <div className="h-80 animate-pulse rounded-3xl bg-slate-200" />
      </div>
    </section>
  );
}
```

```tsx
// frontend/src/pages/dashboard-page.tsx
import { BriefCard } from "../features/dashboard/components/brief-card";
import { DashboardSkeleton } from "../features/dashboard/components/dashboard-skeleton";
import { ModuleSnapshotCard } from "../features/dashboard/components/module-snapshot-card";
import { StatCard } from "../features/dashboard/components/stat-card";
import { useDashboardQuery } from "../features/dashboard/hooks/use-dashboard-query";

export function DashboardPage() {
  const { data, isLoading, isError } = useDashboardQuery();

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (isError || !data) {
    return (
      <section className="rounded-3xl border border-rose-200 bg-rose-50 p-8 text-rose-800">
        Dashboard data is currently unavailable.
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-[0.24em] text-slate-500">Daily Overview</p>
        <h3 className="mt-3 text-3xl font-semibold text-slate-950">{data.title}</h3>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">{data.subtitle}</p>
        <p className="mt-4 text-xs text-slate-500">Updated {data.generatedAtLabel}</p>
      </section>

      <section className="grid grid-cols-5 gap-4">
        {data.stats.map((item) => (
          <StatCard key={item.label} label={item.label} value={item.value} tone={item.tone} />
        ))}
      </section>

      <section className="grid grid-cols-[2fr_1fr] gap-6">
        <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">Primary insight</h3>
          <p className="mt-2 text-sm text-slate-500">Chart integration lands in the next plan; this slice reserves the main dashboard panel and verifies the layout contract.</p>
          <div className="mt-6 h-80 rounded-2xl bg-slate-100" />
        </article>
        <div className="space-y-6">
          <BriefCard title="Today Brief" items={data.briefItems} />
          <BriefCard title="Data Status" items={data.statusItems.map((item) => `${item.label}: ${item.detail}`)} />
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Module snapshots</h3>
          <p className="mt-1 text-sm text-slate-500">Jump from the homepage into the dedicated workbench pages.</p>
        </div>
        <div className="grid grid-cols-3 gap-4">
          {data.snapshots.map((item) => (
            <ModuleSnapshotCard key={item.title} {...item} />
          ))}
        </div>
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Re-run the dashboard tests and the frontend test suite**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run src/features/dashboard/__tests__/dashboard-page.test.tsx
cmd /c npm --prefix frontend run test -- --run
cmd /c npm --prefix frontend run build
```

Expected:

- The dashboard page test passes
- The bootstrap and route-shell tests still pass
- The Vite build succeeds with the new dashboard code

- [ ] **Step 5: Commit the dashboard foundation**

```bash
git add frontend
git commit -m "feat: add dashboard foundation page"
```

### Task 4: Teach FastAPI to serve the compiled SPA for workbench routes

**Files:**
- Create: `src/app/web/spa_assets.py`
- Create: `tests/test_task11_frontend_spa_serving.py`
- Modify: `src/app/web/fastapi_app.py`

- [ ] **Step 1: Add failing backend tests for SPA route serving**

```python
# tests/test_task11_frontend_spa_serving.py
from pathlib import Path

from src.app.web.spa_assets import resolve_spa_index, should_serve_spa_path


def test_should_serve_spa_path_only_for_workbench_routes():
    assert should_serve_spa_path("/")
    assert should_serve_spa_path("/dashboard")
    assert should_serve_spa_path("/news")
    assert should_serve_spa_path("/settings")
    assert not should_serve_spa_path("/api/frontend/dashboard")
    assert not should_serve_spa_path("/healthz")
    assert not should_serve_spa_path("/static/app.js")


def test_resolve_spa_index_returns_none_when_dist_is_missing(tmp_path: Path):
    assert resolve_spa_index(tmp_path) is None


def test_resolve_spa_index_returns_index_file_when_present(tmp_path: Path):
    dist_dir = tmp_path / "frontend" / "dist"
    dist_dir.mkdir(parents=True)
    index_file = dist_dir / "index.html"
    index_file.write_text("<!doctype html><div id=\"root\"></div>", encoding="utf-8")

    resolved = resolve_spa_index(dist_dir)

    assert resolved == index_file
```

- [ ] **Step 2: Run the backend SPA tests to verify they fail**

Run:

```powershell
uv run python -m pytest tests/test_task11_frontend_spa_serving.py -q
```

Expected:

- pytest fails because `src.app.web.spa_assets` does not exist yet

- [ ] **Step 3: Implement the SPA asset helper and FastAPI integration**

```python
# src/app/web/spa_assets.py
from __future__ import annotations

from pathlib import Path


WORKBENCH_ROUTES = {
    "/",
    "/dashboard",
    "/news",
    "/macro",
    "/market",
    "/events",
    "/push",
    "/settings",
}


def should_serve_spa_path(path: str) -> bool:
    return path in WORKBENCH_ROUTES


def resolve_spa_index(dist_dir: Path) -> Path | None:
    index_file = dist_dir / "index.html"
    return index_file if index_file.exists() else None
```

```python
# src/app/web/fastapi_app.py
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from .spa_assets import resolve_spa_index
```

```python
# src/app/web/fastapi_app.py
    frontend_dist_dir = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    frontend_index = resolve_spa_index(frontend_dist_dir)
```

```python
# src/app/web/fastapi_app.py
    @app.get("/", response_class=FileResponse)
    def homepage() -> FileResponse | RedirectResponse:
        if frontend_index is not None:
            return RedirectResponse("/dashboard", status_code=307)
        return FileResponse(static_dir / "index.html")

    @app.get("/dashboard", response_class=FileResponse)
    @app.get("/news", response_class=FileResponse)
    @app.get("/macro", response_class=FileResponse)
    @app.get("/market", response_class=FileResponse)
    @app.get("/events", response_class=FileResponse)
    @app.get("/push", response_class=FileResponse)
    @app.get("/settings", response_class=FileResponse)
    def spa_workbench() -> FileResponse | HTMLResponse:
        if frontend_index is not None:
            return FileResponse(frontend_index)
        return HTMLResponse(
            render_error_html("Workbench unavailable", "Build the frontend bundle before opening the SPA routes."),
            status_code=503,
        )
```

```python
# src/app/web/fastapi_app.py
    @app.get("/{_:path}", response_class=HTMLResponse)
    def not_found(_: str) -> HTMLResponse:
        return HTMLResponse(
            render_error_html("Page not found", "The requested dashboard route does not exist."),
            status_code=404,
        )
```

- [ ] **Step 4: Run backend tests and the current web shell regression suite**

Run:

```powershell
uv run python -m pytest tests/test_task11_frontend_spa_serving.py -q
uv run python -m pytest tests/test_task03_web_app_shell.py -q
```

Expected:

- The new SPA serving tests pass
- Existing Task 03 tests still pass because `/legacy` and the legacy static fallback remain intact

- [ ] **Step 5: Commit the backend SPA serving changes**

```bash
git add src/app/web/spa_assets.py src/app/web/fastapi_app.py tests/test_task11_frontend_spa_serving.py
git commit -m "feat: serve frontend spa from fastapi"
```

### Task 5: Document the new developer workflow and verify the full slice

**Files:**
- Modify: `README.md`
- Modify: `README.zh.md`

- [ ] **Step 1: Update the English and Chinese README files with the frontend workflow**

````md
<!-- README.md -->
## Frontend workspace

The new SPA frontend lives in `frontend/` and is built with Vite + React + TypeScript.

Install frontend dependencies:

```powershell
cmd /c npm --prefix frontend install
```

Run the frontend dev server:

```powershell
cmd /c npm --prefix frontend run dev
```

Build the frontend bundle for FastAPI to serve:

```powershell
cmd /c npm --prefix frontend run build
```
````

````md
<!-- README.zh.md -->
## 前端工作台

新的 SPA 前端位于 `frontend/`，技术栈为 `Vite + React + TypeScript`。

安装前端依赖：

```powershell
cmd /c npm --prefix frontend install
```

启动前端开发服务器：

```powershell
cmd /c npm --prefix frontend run dev
```

构建给 FastAPI 提供的前端产物：

```powershell
cmd /c npm --prefix frontend run build
```
````

- [ ] **Step 2: Run the full verification set**

Run:

```powershell
cmd /c npm --prefix frontend run test -- --run
cmd /c npm --prefix frontend run build
uv run python -m pytest tests/test_task11_frontend_spa_serving.py tests/test_task03_web_app_shell.py -q
```

Expected:

- All frontend tests pass
- Frontend production build succeeds
- Backend SPA serving regressions pass

- [ ] **Step 3: Start the backend and confirm the route behavior manually**

Run:

```powershell
uv run python main.py web --host 127.0.0.1 --port 8000 --no-reload
```

Manual checks:

- `http://127.0.0.1:8000/` redirects to `/dashboard` after `frontend/dist/index.html` exists
- `http://127.0.0.1:8000/dashboard` serves the SPA shell
- `http://127.0.0.1:8000/legacy` still serves the legacy page
- `http://127.0.0.1:8000/api/frontend/dashboard` still returns JSON

- [ ] **Step 4: Commit the docs and verification updates**

```bash
git add README.md README.zh.md
git commit -m "docs: add frontend workspace workflow"
```

- [ ] **Step 5: Record the follow-on planning boundary**

Add this note to the implementation handoff or PR description:

```text
This slice intentionally stops after the shell, route skeleton, dashboard foundation, and FastAPI SPA serving integration. The next plans should cover module pages (News/Macro/Market/Events) and operational pages (Push Center/Settings).
```

## Self-Review

### Spec coverage

- Modern SPA stack: covered in Task 1
- Sidebar/Header/App Shell: covered in Task 2
- Dashboard homepage: covered in Task 3
- FastAPI serving strategy: covered in Task 4
- Documentation and verification: covered in Task 5
- Deferred modules and operations pages: explicitly split into follow-on plans to keep this slice independently shippable

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” instructions appear in tasks
- Commands, file paths, and test entrypoints are explicit
- All code-producing steps include concrete file contents

### Type consistency

- `DashboardPage` consumes `useDashboardQuery`
- `useDashboardQuery` consumes `getDashboard` and `adaptDashboard`
- Shell route metadata consistently uses `title` and `description`
- SPA backend helper consistently uses `resolve_spa_index`
