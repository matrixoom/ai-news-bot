# AI News Bot

This repository now provides two main capabilities:

- A FastAPI web app with a separated frontend (static SPA + JSON API)
- A push-report job for automated channel delivery

## Current Architecture

### Frontend

- Static app served from `src/app/web/static/`
- Sidebar layout with independent modules:
  - Hot News
  - Macro Trend (last 12 months line charts)
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

- `web` mode (default): starts FastAPI app
- `push` mode: runs push report job

## Quick Start (Local)

### 1. Python version

- Recommended: Python `3.12.x`

### 2. Install dependencies

PowerShell:

```powershell
uv python install 3.12
uv sync --python 3.12
```

If you hit a Windows cache permission error like:
`Failed to initialize cache at C:\Users\...\AppData\Local\uv\cache`,
run with project-local cache:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv sync --python 3.12
```

### 3. Run web app

```powershell
uv run python main.py web --host 127.0.0.1 --port 8000
```

Open:

- `http://127.0.0.1:8000/` (frontend page)

### 4. Run push job

```powershell
uv run python main.py push
```

## API Endpoints

| Path                      | Method | Description |
| ------------------------- | ------ | ----------- |
| `/`                       | GET    | Frontend app (static entry) |
| `/api/frontend/dashboard` | GET    | Frontend-oriented aggregated payload |
| `/api/dashboard`          | GET    | Legacy dashboard payload |
| `/legacy`                 | GET    | Legacy server-rendered page |
| `/healthz`                | GET    | Health check |

## Data Mode Notes

In `web` mode, the server runs with `prefer_live_data=True`:

- It tries live providers first
- If live providers are unavailable (missing keys/network/deps), it falls back to sample providers
- This keeps the UI available even when real data is partially unavailable

## Real Interface Minimal Tests

Minimal real-interface tests are in:

- `tests/test_real_interface_minimal.py`

Run default (unit-level with mocked HTTP calls):

```powershell
uv run python -m unittest tests.test_real_interface_minimal
```

Run optional live smoke test:

```powershell
$env:RUN_LIVE_SMOKE='1'
uv run python -m unittest tests.test_real_interface_minimal
```

## Verified Local Run (2026-03-19)

Validated by starting `main.py web` and checking:

- `/` returned `200`
- `/static/app.js` returned `200`
- `/api/frontend/dashboard` returned `200`
- `news_sections[0].items` count was `10`
- `/legacy` returned `200`

## Key Files

- `main.py`
- `src/app/web/server.py`
- `src/app/web/fastapi_app.py`
- `src/app/web/frontend_payload.py`
- `src/app/web/static/index.html`
- `src/app/web/static/styles.css`
- `src/app/web/static/app.js`
