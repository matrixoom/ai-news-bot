#!/usr/bin/env python3
"""Main application entrypoint for the dashboard web app and push job."""
from __future__ import annotations

import argparse
import sys
from typing import Sequence

from src.app.jobs.push_job import run_push_job
from src.app.web import run_dev_server
from src.services.macro_data_sync_service import MacroDataSyncService


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the project entrypoint."""
    parser = argparse.ArgumentParser(
        description="Run the finance and policy dashboard web app or the push workflow.",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("web", "push", "macro-sync"),
        default="web",
        help="Execution mode. Defaults to 'web'.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for the web server in web mode.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for the web server in web mode.",
    )
    parser.add_argument(
        "--reload",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable hot reload for the web server in web mode. Use --no-reload to disable it.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Route execution to the web app by default or the push job when requested."""
    args = build_parser().parse_args(argv)

    if args.mode == "push":
        return run_push_job()

    if args.mode == "macro-sync":
        result = MacroDataSyncService().sync_gdp_history()
        print(f"Macro Data GDP sync complete: {result}")
        return 0

    run_dev_server(host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
