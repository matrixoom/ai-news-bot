# 10. Local Dev Environment And Debug

## 状态

Completed for implementation phase.

## Goal

Standardize this repository on a stable local Python environment managed by `uv`, and make VS Code debugging work against the project-local `.venv`.

## Chosen Baseline

- Python version: `3.12`
- Environment location: [`.venv`](/d:/E/documents/gitspaces/ai-news-bot/.venv)
- Dependency source of truth: [`pyproject.toml`](/d:/E/documents/gitspaces/ai-news-bot/pyproject.toml)
- Version selector: [`.python-version`](/d:/E/documents/gitspaces/ai-news-bot/.python-version)
- VS Code debug config: [`.vscode/launch.json`](/d:/E/documents/gitspaces/ai-news-bot/.vscode/launch.json)

Python `3.14` is available on this machine, but this project is pinned to `3.12` to avoid dependency breakage on very new interpreter releases.

## Operational Rule

Treat the repository-local [`.venv`](/d:/E/documents/gitspaces/ai-news-bot/.venv) as the only supported runtime environment for this project.

- Preferred command pattern: `uv run ...`
- Direct interpreter path on Windows: [`.venv\Scripts\python.exe`](/d:/E/documents/gitspaces/ai-news-bot/.venv/Scripts/python.exe)
- Do not rely on the system `python` executable when running the app or tests
- If commands report missing modules such as `fastapi`, `feedparser`, or `pytest`, first verify that the command is using `.venv`

Quick verification:

```powershell
uv run python --version
uv run python -c "import sys; print(sys.executable)"
```

Environment repair:

```powershell
uv sync --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

## One-Time Setup

Run these commands from the repository root:

```powershell
uv python install 3.12
uv sync --python 3.12
```

## Daily Workflow

Preferred commands:

```powershell
uv sync
uv run python main.py
uv run python main.py --host 127.0.0.1 --port 8000
uv run python main.py push
uv run python -m unittest tests.test_task09_integration_suite
```

## VS Code Debug

Available launch targets now include:

- `Python: Current File (uv .venv)`
- `Python: Current File With Args (uv .venv)`
- `Python: Project Main Entrypoint (uv .venv)`
- `Python: Push Job Via Main (uv .venv)`
- `Python: Web Shell (uv .venv)`
- `Python: Full Regression Suite (uv .venv)`

## Verification

Use these checks after setup:

```powershell
uv run python --version
uv run python -m unittest tests.test_task01_architecture tests.test_task02_provider_strategy tests.test_task03_web_app_shell tests.test_task04_news_pipeline tests.test_task05_macro_monitoring tests.test_task06_market_models tests.test_task07_events_outlook tests.test_task08_push_workflow tests.test_task09_integration_suite tests.test_task10_local_dev_environment tests.test_main_entrypoint tests.test_live_provider_fallbacks
```
