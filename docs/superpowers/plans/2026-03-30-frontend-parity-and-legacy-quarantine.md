# Frontend Parity And Legacy Quarantine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the frontend migration by restoring parity-critical workbench features in the new React SPA, then quarantine superseded legacy frontend code under `to_delete/` for manual review before deletion.

**Architecture:** Keep FastAPI as the single serving layer and finish the SPA so it becomes the primary workbench for both read-heavy and operational flows. Migrate remaining behavior in bounded slices: shared shell controls first, then operational pages (`Push Center`, `Settings`, `Status`), then quarantine the old static runtime without deleting it.

**Tech Stack:** FastAPI, React, TypeScript, Tailwind CSS, React Router, TanStack Query, Vitest, Testing Library, pytest

---

## Scope Note

This plan covers the remaining parity-critical migration work:

- shell controls and state
- `Push Center`
- `Settings`
- `Status`
- legacy code quarantine into `to_delete/`

It does **not** attempt a full visual redesign or a deep charting overhaul beyond parity-critical behavior. If richer chart interactions are still needed after this slice, write a follow-up plan for chart/workbench polish.

## File Structure

### Shared shell state and controls

- `frontend/src/app/providers.tsx`
  - query client and shared provider setup
- `frontend/src/layouts/app-shell.tsx`
  - shell composition for sidebar, header, outlet
- `frontend/src/layouts/header-bar.tsx`
  - top-level controls, theme toggle, ticker, freshness, route actions
- `frontend/src/layouts/sidebar-nav.tsx`
  - navigation plus mode/status chrome
- `frontend/src/shared/config/nav-items.ts`
  - navigation metadata including status route
- `frontend/src/shared/hooks/use-theme-preference.ts`
  - local theme persistence and document binding
- `frontend/src/shared/hooks/use-market-ticker.ts`
  - shell ticker data derivation from dashboard or market data
- `frontend/src/shared/hooks/use-news-mode.ts`
  - URL-driven and persisted news mode state
- `frontend/src/shared/ui/news-mode-switch.tsx`
  - shell-level mode switch
- `frontend/src/shared/ui/theme-toggle.tsx`
  - theme toggle button
- `frontend/src/shared/ui/market-ticker.tsx`
  - compact shell ticker

### Status page

- `frontend/src/pages/status-page.tsx`
  - dedicated operational status page
- `frontend/src/features/status/api/get-status-module.ts`
  - fetch status payload
- `frontend/src/features/status/model/status-module.types.ts`
  - raw/view model types
- `frontend/src/features/status/model/status-module-adapter.ts`
  - payload adapter
- `frontend/src/features/status/hooks/use-status-module-query.ts`
  - query hook
- `frontend/src/features/status/components/status-summary-card.tsx`
  - status summary UI

### Push Center

- `frontend/src/pages/push-page.tsx`
  - new Push Center page
- `frontend/src/features/push/api/get-push-module.ts`
  - fetch push module payload
- `frontend/src/features/push/api/update-push-config.ts`
  - save config request
- `frontend/src/features/push/api/preview-push.ts`
  - preview request
- `frontend/src/features/push/api/trigger-push.ts`
  - send request
- `frontend/src/features/push/model/push-module.types.ts`
  - raw/view model types
- `frontend/src/features/push/model/push-module-adapter.ts`
  - payload adapter
- `frontend/src/features/push/hooks/use-push-module-query.ts`
  - main query hook
- `frontend/src/features/push/components/push-config-form.tsx`
  - config form
- `frontend/src/features/push/components/push-preview-panel.tsx`
  - preview pane
- `frontend/src/features/push/components/push-schedules-editor.tsx`
  - schedule editing
- `frontend/src/features/push/components/push-run-history.tsx`
  - recent runs table

### Settings page

- `frontend/src/pages/settings-page.tsx`
  - new Settings page
- `frontend/src/features/settings/model/settings-view-model.ts`
  - page sections derived from runtime preferences and available defaults
- `frontend/src/features/settings/components/settings-section-card.tsx`
  - reusable settings section shell

### Routing and tests

- `frontend/src/app/routes.tsx`
  - wire `push`, `settings`, and `status`
- `frontend/src/app/__tests__/router-shell.test.tsx`
  - shell route coverage updates
- `frontend/src/features/status/__tests__/status-page.test.tsx`
  - status page tests
- `frontend/src/features/push/__tests__/push-page.test.tsx`
  - push center tests
- `frontend/src/features/settings/__tests__/settings-page.test.tsx`
  - settings page tests
- `tests/test_task11_frontend_spa_serving.py`
  - backend SPA serving coverage for assets and routes
- `src/app/web/fastapi_app.py`
  - keep SPA asset serving and route table aligned

### Legacy quarantine

- `to_delete/legacy-frontend/static/index.html`
  - quarantined copy of the old static shell
- `to_delete/legacy-frontend/static/styles.css`
  - quarantined copy of the old shell styles
- `to_delete/legacy-frontend/static/app.js`
  - quarantined copy of the old runtime
- `docs/frontend-migration-gap-audit-2026-03-30.md`
  - migration audit and removal rationale
- `README.md`
  - note about legacy quarantine and review process
- `README.zh.md`
  - Chinese note about legacy quarantine and review process

---

## Task Overview

1. Stabilize the current merged branch and keep SPA asset serving green.
2. Restore shell-level controls and add a real `Status` route.
3. Migrate `Push Center`.
4. Migrate `Settings`.
5. Verify parity-critical behavior.
6. Move superseded legacy frontend code into `to_delete/` instead of deleting it.

## Verification Target

At the end of this plan, all of the following should be true:

- `/dashboard`, `/news`, `/macro`, `/market`, `/events`, `/push`, `/settings`, `/status` open in the SPA
- `Push Center` works for load / save / preview / trigger flows
- shell has theme toggle, news mode switch, and ticker/freshness controls
- legacy frontend runtime is no longer the active implementation path
- superseded legacy code exists under `to_delete/` for manual audit
- backend tests and frontend tests pass

