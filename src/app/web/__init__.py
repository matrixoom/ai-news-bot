"""Web entrypoints."""

from .app import create_web_app
from .fastapi_app import create_fastapi_app
from .server import run_dev_server

__all__ = ["create_fastapi_app", "create_web_app", "run_dev_server"]
