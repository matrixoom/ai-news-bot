# 10. Local Dev Environment And Debug

## Goal

Standardize this repository on a stable local Python environment managed by `uv`, and make VS Code debugging work against the project-local `.venv`.

## Chosen Baseline

- Python version: `3.12`
- Environment location: [`.venv`](d:\E\documents\gitspaces\ai-news-bot\.venv)
- Dependency source of truth: [`pyproject.toml`](d:\E\documents\gitspaces\ai-news-bot\pyproject.toml)
- Version selector: [`.python-version`](d:\E\documents\gitspaces\ai-news-bot\.python-version)
- VS Code debug config: [`.vscode/launch.json`](d:\E\documents\gitspaces\ai-news-bot\.vscode\launch.json)

Python `3.14` is available on this machine, but this project is now pinned to `3.12` to avoid dependency breakage on very new interpreter releases.

## One-Time Setup

Run these commands from the repository root:

```powershell
uv python install 3.12
uv sync --python 3.12
```

What this does:

- downloads or reuses a managed Python 3.12 interpreter
- creates [`.venv`](d:\E\documents\gitspaces\ai-news-bot\.venv)
- installs dependencies from [`pyproject.toml`](d:\E\documents\gitspaces\ai-news-bot\pyproject.toml)
- writes `uv.lock` for reproducible restores

## Daily Workflow

Preferred commands:

```powershell
uv sync
uv run python main.py
uv run python -m src.app.web.server
uv run python -m unittest tests.test_task01_architecture
```

Optional shell activation on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
deactivate
```

## Add Or Update Dependencies

Recommended:

```powershell
uv add requests
uv add --dev pytest
uv remove requests
```

If you must keep compatibility with the old file during migration:

```powershell
uv export --format requirements-txt --no-hashes > requirements.txt
```

## VS Code Debug

Available launch targets:

- `Python: Current File (uv .venv)`
- `Python: Current File With Args (uv .venv)`
- `Python: Legacy Push Entrypoint (uv .venv)`
- `Python: Web Shell (uv .venv)`
- `Python: Task 01 Tests (uv .venv)`

The `With Args` configuration prompts for command-line arguments at launch time, which is the manual debug entry for ad hoc scripts.

## Verification

Use these checks after setup:

```powershell
uv run python --version
uv run python -m unittest tests.test_task01_architecture
```

If VS Code does not auto-detect the interpreter, manually select:

```text
${workspaceFolder}\.venv\Scripts\python.exe
```
