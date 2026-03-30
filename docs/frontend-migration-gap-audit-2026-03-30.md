# Frontend Migration Gap Audit

Date: `2026-03-30`

## Current Verdict

The new React SPA is **not** a full replacement for the legacy frontend yet.

What exists today is a **partial migration**:

- The new SPA owns the top-level workbench shell and the read-heavy analysis pages.
- The legacy static frontend still contains several operational and richer interaction flows.
- Both implementations currently coexist, which makes the repo and behavior feel inconsistent.

## What Has Been Migrated

These routes now exist in the new SPA under `frontend/`:

- `Dashboard`
- `News`
- `Macro`
- `Market`
- `Events`

Evidence:

- `frontend/src/app/routes.tsx`
- `frontend/src/pages/dashboard-page.tsx`
- `frontend/src/pages/news-page.tsx`
- `frontend/src/pages/macro-page.tsx`
- `frontend/src/pages/market-page.tsx`
- `frontend/src/pages/events-page.tsx`

## What Is Still Missing Or Incomplete

### 1. Push Center is not migrated

The legacy frontend still contains a full operational Push workspace with:

- channel type selection
- report style selection
- SMTP/email config form
- module selection
- preview iframe
- save / preview / send actions
- schedule editing
- recent runs table

Evidence in legacy code:

- `src/app/web/static/app.js`
  - `renderPushWorkspace`
  - `renderPushRecentRunsTable`
  - `renderPushPreviewFrame`
  - `collectPushDraft`
  - `requestPushApi`

Current SPA state:

- `/push` still renders `ModulePlaceholderPage`
- no Push page exists in `frontend/src/pages/`

Evidence:

- `frontend/src/app/routes.tsx`
- `frontend/src/pages/module-placeholder-page.tsx`

### 2. Settings is not migrated

Current SPA state:

- `/settings` still renders `ModulePlaceholderPage`

Legacy implication:

- Settings-like behavior still lives implicitly inside the old shell and module runtime, rather than a dedicated SPA page.

Evidence:

- `frontend/src/app/routes.tsx`
- `frontend/src/pages/module-placeholder-page.tsx`

### 3. Status module is not represented as a real SPA page

The backend still exposes a status module payload:

- `frontend_status_module`

But the new SPA navigation and routes do not include a dedicated status page.

Evidence:

- `src/app/web/fastapi_app.py`
- `frontend/src/shared/config/nav-items.ts`
- `frontend/src/app/routes.tsx`

### 4. News mode switching was reduced

Legacy behavior included:

- switching `hybrid / api / upstream`
- writing the selected mode into URL query params
- refreshing dependent modules after mode change

Evidence:

- `src/app/web/static/app.js`
  - `renderModeSwitch`
  - `getRequestedNewsMode`
  - `setRequestedNewsMode`

Current SPA state:

- News mode options and upstream status are displayed
- but there is no route-level or header-level mode switch UI that actually changes backend mode

Evidence:

- `frontend/src/pages/news-page.tsx`
- `frontend/src/features/news/components/news-status-panel.tsx`

### 5. Top ticker, theme toggle, and shell-level controls were reduced

Legacy shell included:

- theme toggle
- top ticker fed by market state
- richer shell behavior and module-driven chrome

Evidence:

- `src/app/web/static/index.html`
- `src/app/web/static/app.js`
  - `renderThemeToggle`
  - `applyTheme`
  - `renderTickerFromState`

Current SPA shell only includes:

- page title
- page description
- a simple refresh button
- a static `Freshness: live` label

Evidence:

- `frontend/src/layouts/header-bar.tsx`
- `frontend/src/layouts/app-shell.tsx`
- `frontend/src/layouts/sidebar-nav.tsx`

### 6. Dashboard is simplified compared with the legacy workbench

The new Dashboard gives a cleaner structure, but it currently omits shell-level richness such as:

- top ticker behavior
- theme interactions
- module orchestration feel
- operational feed / recent runs style elements from the old workbench

Evidence:

- `frontend/src/pages/dashboard-page.tsx`
- compared with the richer orchestration in `src/app/web/static/app.js`

### 7. Chart interaction depth is reduced

Legacy implementation includes:

- market range switching
- macro range switching
- ECharts orchestration and redraw behavior

Evidence:

- `src/app/web/static/app.js`
  - `renderMarketChartRangeSwitch`
  - `renderMarketTrendChart`
  - `renderMacroChartRangeSwitch`
  - `renderMacroComparisonChart`

Current SPA:

- keeps calmer summary views
- does not yet preserve the same chart control depth or runtime richness

Evidence:

- `frontend/src/pages/macro-page.tsx`
- `frontend/src/pages/market-page.tsx`

## Why The Codebase Feels Messy

### 1. Two frontends are still alive

Both of these currently matter:

- new SPA: `frontend/`
- legacy frontend: `src/app/web/static/`

This is the main reason the repo feels split-brain.

### 2. The legacy runtime still contains a large amount of product behavior

The old file `src/app/web/static/app.js` is still carrying:

- module orchestration
- push center behavior
- shell behavior
- charts
- preview logic
- config updates

So even after adding the new SPA, the old frontend is still the only place where some real features exist.

### 3. Migration is route-complete but not feature-complete

The app can open the new SPA routes, but some routes are placeholders and some migrated routes are reduced versions of the old behavior.

### 4. Temporary migration artifacts remain in the repo

Current repo clutter also includes:

- `.merge-backups/`
- `.superpowers/`
- legacy plan docs and intermediate notes

These are not the root problem, but they amplify the feeling of disorder.

## Practical Status Matrix

### New SPA is production-usable for

- dashboard overview reading
- news review
- macro review
- market review
- events review

### Legacy frontend is still required for

- push workspace operations
- scheduling
- preview/send workflow
- some richer shell interactions
- some higher-interaction chart/runtime behaviors

## Recommended Next Move

Do **not** delete the legacy frontend yet.

The safest next phase is:

1. Build a migration checklist per feature, not per file.
2. Migrate `Push Center`.
3. Migrate `Settings`.
4. Decide whether `Status` becomes a first-class page or stays embedded.
5. Reintroduce any shell-level controls that still matter:
   - news mode switching
   - theme toggle
   - ticker / freshness behavior
6. Only after feature parity is acceptable:
   - remove legacy static runtime
   - delete backup and migration leftovers
   - simplify the repo structure

## Immediate Priority List

Highest priority gaps:

- `Push Center`
- `Settings`
- `Status`
- `News mode switch`
- `Shell-level controls`

Secondary gaps:

- richer chart controls
- dashboard operational feed
- final codebase cleanup
