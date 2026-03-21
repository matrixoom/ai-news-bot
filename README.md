# AI News Bot

This repository provides two runtime capabilities:

- A FastAPI web app with a separated frontend
- A push-report job for automated channel delivery

## Architecture

### Frontend

- Static SPA served from `src/app/web/static/`
- Main modules:
  - Hot News
  - Macro Trend
  - Market Models
  - Events Outlook
  - Data Status
- Entry: `/`

### Backend

- FastAPI app: `src/app/web/fastapi_app.py`
- Frontend payload API: `/api/frontend/dashboard`
- Legacy structured API: `/api/dashboard`
- Legacy SSR page: `/legacy`
- Health check: `/healthz`

## Runtime Modes

The CLI entrypoint is `main.py`:

- `web`: starts the FastAPI app
- `push`: runs the push-report job

## Quick Start

### 1. Python

- Recommended: `Python 3.12.x`

### 2. Install Python dependencies

```powershell
uv python install 3.12
uv sync --python 3.12
```

If `uv` hits a Windows cache permission issue, use a project-local cache:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv sync --python 3.12
```

### 3. Initialize the NewsNow submodule

`.third_part_newsnow` is treated as a third-party upstream project. The expected workflow is:

- keep it as a git submodule
- avoid changing its source code in normal development
- update it explicitly when you want the latest upstream code

Initialize the pinned submodule commit and install its dependencies:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/init-newsnow-submodule.ps1
```

If you want to move the submodule to the latest upstream commit:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/init-newsnow-submodule.ps1 -UpdateRemote
```

If you only want to sync/init the submodule without running `npm install`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/init-newsnow-submodule.ps1 -SkipInstall
```

### 4. Run the web app

```powershell
uv run python main.py web --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`.

### 5. Run the push job

```powershell
uv run python main.py push
```

## Full Local Workflow

### 1. Initialize Python dependencies

```powershell
uv python install 3.12
uv sync --python 3.12
```

### 2. Initialize the NewsNow submodule

```powershell
powershell -ExecutionPolicy Bypass -File scripts/init-newsnow-submodule.ps1
```

### 3. Start the main web app

```powershell
uv run python main.py web --host 127.0.0.1 --port 8000
```

### 4. Open the frontend

```text
http://127.0.0.1:8000/
```

### 5. Switch news mode when needed

- `hybrid`: `http://127.0.0.1:8000/?news_mode=hybrid`
- `api`: `http://127.0.0.1:8000/?news_mode=api`
- `upstream`: `http://127.0.0.1:8000/?news_mode=upstream`

## News Modes

The dashboard supports three news data modes:

- `hybrid`: use NewsNow aggregated API first, then fall back to upstream source fetching
- `api`: use NewsNow aggregated API only
- `upstream`: fetch from the local NewsNow upstream project

Frontend requests accept `?news_mode=hybrid|api|upstream`.

Example:

```text
http://127.0.0.1:8000/?news_mode=upstream
```

## Upstream Service Startup

When the app uses `upstream` mode, it will try to auto-start the local NewsNow dev server if it is not already running.

For manual debugging, start the upstream project yourself:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-newsnow-upstream.ps1
```

Stop it with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-newsnow-upstream.ps1
```

Default upstream address:

- `http://127.0.0.1:5173`

Optional environment overrides:

- `NEWSNOW_UPSTREAM_PROJECT_DIR`
- `NEWSNOW_UPSTREAM_BASE_URL`

## Status Checks

### Check main app status

```powershell
Invoke-WebRequest http://127.0.0.1:8000/healthz -UseBasicParsing
```

### Check upstream service status

```powershell
Invoke-WebRequest http://127.0.0.1:5173/healthz -UseBasicParsing
```

### Check whether port `8000` is listening

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

### Check whether port `5173` is listening

```powershell
Get-NetTCPConnection -LocalPort 5173 -State Listen
```

### Find which process owns the upstream port

```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 5173 -State Listen).OwningProcess
```

If you changed the app port or upstream port, replace `8000` or `5173` with the actual value.

## Stop Commands

### Stop the main app

If it is running in the current terminal, press `Ctrl + C`.

If it is running in the background on port `8000`:

```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess -Force
```

### Stop the upstream NewsNow dev server

If it is running in the current terminal, press `Ctrl + C`.

If it is running in the background on port `5173`:

```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 5173 -State Listen).OwningProcess -Force
```

Or use the helper script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-newsnow-upstream.ps1
```

### Stop both services

```powershell
$main = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($main) { Stop-Process -Id $main.OwningProcess -Force }
$upstream = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($upstream) { Stop-Process -Id $upstream.OwningProcess -Force }
```

## Keeping the Submodule Clean

If generated files inside `.third_part_newsnow` become dirty after running the upstream project, restore the tracked generated files with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/clean-newsnow-submodule.ps1
```

This is intended to reduce unnecessary diffs in the third-party submodule.

If the NewsNow dev server is still running, generated files such as `src/routeTree.gen.ts` may be rewritten immediately. Stop the upstream dev server first, then run the cleanup script.

## API Endpoints

| Path                      | Method | Description |
| ------------------------- | ------ | ----------- |
| `/`                       | GET    | Frontend app entry |
| `/api/frontend/dashboard` | GET    | Frontend-oriented aggregated payload |
| `/api/dashboard`          | GET    | Legacy dashboard payload |
| `/legacy`                 | GET    | Legacy server-rendered page |
| `/healthz`                | GET    | Health check |

## Data Mode Notes

In `web` mode, the app runs with `prefer_live_data=True`:

- it tries live providers first
- if live providers are unavailable, it falls back to sample providers
- this keeps the UI available when part of the real data path fails

## Tests

Run the main regression set:

```powershell
uv run python -m pytest tests/test_task03_web_app_shell.py tests/test_task04_news_pipeline.py tests/test_live_provider_fallbacks.py tests/test_task04_newsnow_integration.py -q
```

Run the live full-source NewsNow matrix:

```powershell
$env:RUN_LIVE_NEWSNOW_ALL_SOURCES='1'
uv run python -m pytest tests/test_task04_newsnow_integration.py -k NewsNowAllSourcesLiveMatrixTests -q
```

## Key Files

- `main.py`
- `src/app/web/fastapi_app.py`
- `src/app/web/frontend_payload.py`
- `src/app/web/static/index.html`
- `src/app/web/static/styles.css`
- `src/app/web/static/app.js`
- `src/providers/newsnow_provider.py`
- `scripts/init-newsnow-submodule.ps1`
- `scripts/start-newsnow-upstream.ps1`
- `scripts/stop-newsnow-upstream.ps1`
- `scripts/clean-newsnow-submodule.ps1`
