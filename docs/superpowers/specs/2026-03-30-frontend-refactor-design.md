# Frontend Refactor Design

Date: 2026-03-30

## 1. Background

The current web frontend is implemented as a server-served static page with large, centralized JavaScript and CSS files under `src/app/web/static/`. It already supports multiple business domains, but the current structure couples view rendering, state management, chart logic, and API handling too tightly, which makes future expansion expensive.

The refactor target is a production-grade frontend suited for an internal research and operations desk today, while keeping a clear upgrade path toward a future SaaS and platformized product.

## 2. Product Positioning

Current positioning:

- Internal research and operations workbench
- Read/write balanced interaction model
- Finance, technology, and data-analysis oriented experience

Future direction:

- May evolve into a formal SaaS/platform product
- Must not over-design for multi-tenant complexity in v1
- Must leave room for future auth, workspace, and preference expansion

## 3. Goals

- Build a modern SPA frontend using `React + Vite + TypeScript + Tailwind CSS + shadcn/ui + ECharts`
- Replace the current single static shell with a modular, scalable frontend architecture
- Introduce a reusable app shell with `Sidebar + Header + Dashboard-style main content`
- Keep the visual language simple, modern, and professional
- Preserve and clarify current business module boundaries
- Make data fetching, page state, UI state, and view models clearly separated

## 4. Non-Goals

- No full SaaS feature set in v1
- No multi-tenant or role matrix implementation in v1
- No heavy admin template adoption
- No attempt to turn the product into a marketing-style public site
- No one-shot rewrite of all backend APIs before frontend work starts

## 5. Design Principles

- Build for internal efficiency first
- Prefer calm, analytical visual hierarchy over flashy dashboard aesthetics
- Keep homepage focused on prioritization, not full detail expansion
- Use module pages for deep analysis and operations
- Encode future extensibility in routing, layout, and state boundaries
- Avoid mixing raw backend payloads directly into page components

## 6. Chosen Technical Direction

Chosen option:

- Standalone SPA frontend workbench

Technology stack:

- `Vite`
- `React`
- `TypeScript`
- `Tailwind CSS`
- `shadcn/ui`
- `ECharts`
- `React Router`
- `TanStack Query`
- `Zustand`

Rationale:

- Best long-term maintainability
- Clean frontend/backend separation
- Strong fit for multi-module workbench UI
- Easier future growth into platformized product structure

## 7. Information Architecture

The product will use a `Dashboard homepage + sidebar-driven independent module pages` model.

Top-level navigation:

- `Dashboard`
- `News`
- `Macro`
- `Market`
- `Events`
- `Push Center`
- `Settings`

The navigation model is business-domain based rather than task-narrative based, because it matches current backend module boundaries and scales more cleanly as the system grows.

## 8. Routing Plan

Primary routes:

- `/dashboard`
- `/news`
- `/macro`
- `/market`
- `/events`
- `/push`
- `/settings`

Secondary views should primarily be handled with tabs and query params instead of deep nested route trees.

Examples:

- `/news?tab=overview`
- `/news?tab=channels`
- `/macro?tab=compare`
- `/market?tab=models`
- `/push?tab=schedules`
- `/settings?tab=preferences`

Reasons:

- Better fit for workbench interaction patterns
- Easier link sharing for a specific analysis state
- Lower routing complexity for v1

## 9. App Shell

### 9.1 Sidebar

Desktop behavior:

- Fixed left sidebar
- Width target: `240px` to `260px`
- Supports expanded and collapsed states

Mobile behavior:

- Drawer-style sidebar

Sidebar structure:

- Brand area
- Main navigation
- Secondary actions area

Content:

- Top: product name and brief descriptor
- Middle: main modules
- Bottom: `Settings`, later extensible to profile, workspace, logout

Interaction:

- Active route highlight with subtle background and side indicator
- Tooltip support in collapsed mode

### 9.2 Header

Header structure:

- Left: page title and short description
- Middle: page-level filters or control slots
- Right: refresh, freshness indicator, theme toggle, user menu

The header should not rely on a fake global search in v1 unless a real search flow is defined later.

## 10. Dashboard Homepage Design

The homepage should use a `data cockpit first` layout with an added `summary/brief area`.

### 10.1 Homepage Responsibilities

- Tell users what matters first today
- Surface important changes across modules
- Provide quick operational status
- Route users into the right module for deeper analysis

### 10.2 Homepage Sections

#### A. Overview Hero

Contains:

- Short daily summary title
- One-line analytical summary
- Last update information
- One or two prominent reminders

#### B. KPI Strip

Contains 4 to 6 cards, such as:

- News coverage
- Macro update status
- Market signal summary
- Event count
- Push task status
- Degraded/anomaly module count

Each card should be concise, clickable, and route into its corresponding module.

#### C. Primary Insight Row

Layout:

- Left: main chart or composite trend panel
- Right: summary stack

Right-side summary stack should include:

- `Today Brief`
- `Risks & Watchlist`
- `Data Status`

This section is the main integration of the chosen homepage direction: data cockpit first, with a brief-oriented summary lane.

#### D. Module Snapshot Grid

Snapshot cards for:

- News
- Macro
- Market
- Events
- Push

Each snapshot card includes:

- Module title
- One-line summary
- Status badge
- One key number or trend
- Entry action

#### E. Operational Feed

Bottom area for:

- Recent push runs
- Latest anomalies or degraded modules
- Upcoming important events
- Recent system activity

## 11. Module Page Designs

### 11.1 News

Purpose:

- Intelligence workbench rather than generic news list

Structure:

- Filters for channels, time range, source mode, refresh
- Channel summary area
- Main news list or grouped cards
- Side summary/status area

Tabs:

- `Overview`
- `Channels`
- `Sources`
- `Brief`

### 11.2 Macro

Purpose:

- Indicator research and comparison page

Structure:

- Time window and indicator selection
- Main comparison chart area
- Explanatory and source sections
- Side conclusions/status area

Tabs:

- `Overview`
- `Compare`
- `Indicators`
- `Sources`

### 11.3 Market

Purpose:

- Signal and model workbench, not a trading terminal

Structure:

- Market scope and signal filters
- Market card matrix
- Main trend chart
- Model table and watchlist

Tabs:

- `Overview`
- `Signals`
- `Models`
- `Watchlist`

### 11.4 Events

Purpose:

- Executable event monitoring panel, not only calendar display

Structure:

- Time window and region filters
- Timeline or calendar view
- Event list and impact summary
- Official links and watch items

Tabs:

- `Timeline`
- `Calendar`
- `Watch`
- `Sources`

### 11.5 Push Center

Purpose:

- Production-style operations tool, not a temporary config page

Structure:

- Current status and next execution summary
- Config and schedule editor area
- Live preview/template area
- History and failure records

Tabs:

- `Overview`
- `Schedules`
- `Templates`
- `History`

### 11.6 Settings

Purpose:

- Single-user preferences in v1, but with clear future platform-ready structure

Tabs:

- `Preferences`
- `Dashboard`
- `Data`
- `System`

Notes:

- `System` is a future-ready bucket for account, workspace, permission, API key, and notification growth
- v1 should avoid a single oversized settings form

## 12. Visual Language

The visual style should feel like a professional research platform.

Style rules:

- Light-first experience
- Neutral/slate base palette
- Small controlled use of blue/cyan as accent
- Minimal shadows
- Moderate border radius
- Clear typography hierarchy
- Strong chart readability
- No flashy large-area gradients or template-like admin styling

Desired impression:

- More like a research desk
- Less like a generic admin template
- Less like a public marketing dashboard

## 13. Frontend Architecture

Recommended directory model:

```text
frontend/
  src/
    app/
    layouts/
    pages/
    features/
      dashboard/
      news/
      macro/
      market/
      events/
      push/
      settings/
    entities/
    shared/
      ui/
      charts/
      hooks/
      lib/
      utils/
      types/
```

Responsibilities:

- `app`: entrypoint, providers, router, theme bootstrap
- `layouts`: shell-level layout components
- `pages`: route-level page assembly
- `features`: business-domain functionality
- `entities`: reusable domain view structures
- `shared`: generic infrastructure and UI

## 14. Component Strategy

Core reusable components:

- `AppShell`
- `SidebarNav`
- `HeaderBar`
- `PageHeader`
- `FilterBar`
- `StatCard`
- `InsightChartCard`
- `BriefCard`
- `StatusSummaryCard`
- `ModuleSnapshotCard`
- `DataTableCard`
- `EventTimelineCard`
- `EmptyState`
- `LoadingState`
- `ErrorState`
- `StatusBadge`
- `LastUpdatedBadge`

These components should establish a consistent UI language across the homepage and all modules.

## 15. Data Layer and State Boundaries

### 15.1 Data Fetching

Use `TanStack Query` for:

- Request lifecycle
- Caching
- Retry policy
- Background refresh
- Query invalidation
- Polling where needed

### 15.2 Routing State

Use `React Router` plus query params for:

- Active page
- Active tab
- Time window
- Some shareable filter state

### 15.3 Local UI State

Use `Zustand` only for lightweight UI state such as:

- Sidebar collapsed state
- Theme preference
- Table column visibility
- Local display preferences

### 15.4 User Preferences

V1:

- Local persistence is acceptable

Future:

- Move preferences to backend-backed settings APIs

## 16. API Integration Strategy

Page components should not directly depend on raw backend payloads.

Recommended layers:

- `API client`
- `adapter/mapper`
- `view model consumer components`

Benefits:

- Better resilience to backend field changes
- Better testability
- Cleaner component contracts

Backend evolution guidance:

- Keep module-level APIs stable
- Add a clearer dashboard-focused aggregate payload where helpful
- Do not require a full backend rewrite before frontend migration starts

## 17. Loading, Empty, and Error Handling

The workbench must handle partially available data gracefully.

Required UX patterns:

- Skeleton loading states
- Partial refresh without blocking the entire page
- Clear module-level error panels
- Clear empty states with preserved page structure
- Stale data badges
- Degraded mode indicators

This is especially important because the product uses multiple data domains and data sources with varying availability.

## 18. Testing Strategy

Recommended testing layers:

- Type/model tests for adapters and mappers
- Component tests for key reusable widgets
- Page tests for major flows
- E2E tests for critical journeys

Critical v1 journeys:

- Dashboard load and module navigation
- News filters and detail flow
- Push config edit and preview flow
- Settings changes and persistence

Priority for early confidence:

- `Dashboard`
- `News`
- `Push`
- `Settings`

## 19. Delivery Plan

### Phase 1: Shell Foundation

- Create Vite React TypeScript app
- Set up routing, theme, query provider, app shell
- Implement base UI primitives and layout system

### Phase 2: Core Analysis Surfaces

- Implement Dashboard
- Implement News
- Implement Macro
- Implement Market

### Phase 3: Operational Modules

- Implement Events
- Implement Push Center
- Implement Settings

### Phase 4: Migration and Hardening

- Deprecate legacy static page path
- Clean up integration boundaries
- Expand tests
- Finalize documentation

## 20. Migration Notes

- Keep the current FastAPI backend as the data provider
- Introduce the new frontend as a separate frontend project
- Mount or serve the built SPA from the current backend entry as needed
- Retain the old static shell temporarily during migration
- Remove the old frontend only after the new workbench reaches stability

## 21. Risks and Mitigations

Risk:

- Rebuilding all modules at once may slow delivery

Mitigation:

- Use phased rollout with shared shell and component system first

Risk:

- Backend payload shape drift may leak into page complexity

Mitigation:

- Enforce adapter layer between API and page components

Risk:

- Push and settings flows may become inconsistent if treated as secondary pages

Mitigation:

- Design them as first-class product surfaces in v1

## 22. Final Design Decision Summary

This refactor will:

- Use a standalone SPA workbench architecture
- Serve an internal research and operations workflow first
- Use a business-domain navigation model
- Use a dashboard homepage with data-cockpit priority plus summary lanes
- Keep module pages focused on deeper analysis and operations
- Balance current practicality with future platform evolution
