"""Minimal web application shell for the architecture migration stage."""
import json
from html import escape
from typing import Callable, Iterable, Tuple

from ...services.dashboard_service import DashboardService



def _response(status: str, body: bytes, content_type: str) -> Tuple[str, list, Iterable[bytes]]:
    headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(body))),
    ]
    return status, headers, [body]



def create_web_app(dashboard_service: DashboardService | None = None) -> Callable:
    """Create a minimal WSGI app for the dashboard shell."""
    service = dashboard_service or DashboardService()

    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/")

        if path == "/healthz":
            status, headers, body = _response(
                "200 OK",
                b'{"status":"ok"}',
                "application/json; charset=utf-8",
            )
            start_response(status, headers)
            return body

        if path == "/api/dashboard":
            snapshot = service.build_snapshot()
            payload = json.dumps(
                {
                    "generated_at": snapshot.generated_at,
                    "title": snapshot.title,
                    "summary": snapshot.summary,
                    "sections": [section.__dict__ for section in snapshot.sections],
                },
                ensure_ascii=True,
            ).encode("utf-8")
            status, headers, body = _response(
                "200 OK",
                payload,
                "application/json; charset=utf-8",
            )
            start_response(status, headers)
            return body

        if path == "/":
            snapshot = service.build_snapshot()
            section_items = "".join(
                (
                    "<li>"
                    f"<strong>{escape(section.title)}</strong> "
                    f"[{escape(section.status)}] - {escape(section.description)}"
                    "</li>"
                )
                for section in snapshot.sections
            )
            html = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <title>{escape(snapshot.title)}</title>
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  </head>
  <body>
    <main>
      <h1>{escape(snapshot.title)}</h1>
      <p>{escape(snapshot.summary)}</p>
      <p>Generated at: {escape(snapshot.generated_at)}</p>
      <ul>{section_items}</ul>
      <p>Health: <a href=\"/healthz\">/healthz</a></p>
      <p>API: <a href=\"/api/dashboard\">/api/dashboard</a></p>
    </main>
  </body>
</html>
""".encode("utf-8")
            status, headers, body = _response(
                "200 OK",
                html,
                "text/html; charset=utf-8",
            )
            start_response(status, headers)
            return body

        status, headers, body = _response(
            "404 Not Found",
            b"Not Found",
            "text/plain; charset=utf-8",
        )
        start_response(status, headers)
        return body

    return app
