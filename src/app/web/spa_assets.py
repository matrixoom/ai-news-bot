"""Helpers for serving the compiled dashboard SPA from FastAPI."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi.responses import HTMLResponse


WORKBENCH_ROUTES = (
    "/push",
    "/settings",
)


@dataclass(frozen=True)
class SpaAssets:
    dist_dir: Path
    index_path: Path

    @property
    def is_available(self) -> bool:
        return self.index_path.is_file()


def load_spa_assets() -> SpaAssets:
    repo_root = Path(__file__).resolve().parents[3]
    dist_dir = repo_root / "frontend" / "dist"
    return SpaAssets(dist_dir=dist_dir, index_path=dist_dir / "index.html")


def build_spa_unavailable_response(spa_assets: SpaAssets) -> HTMLResponse:
    return HTMLResponse(
        (
            "<!doctype html>"
            "<html lang='en'>"
            "<head><meta charset='utf-8'><title>Workbench unavailable</title></head>"
            "<body>"
            "<main>"
            "<h1>Workbench unavailable</h1>"
            "<p>The dashboard workbench is not ready yet.</p>"
            f"<p>Expected compiled SPA entry at <code>{spa_assets.index_path.as_posix()}</code>.</p>"
            "</main>"
            "</body>"
            "</html>"
        ),
        status_code=503,
    )
