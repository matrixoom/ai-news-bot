"""Legacy WSGI web entrypoint after dashboard removal."""
from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus


def render_error_html(title: str, message: str) -> bytes:
    """渲染通用错误页。

    Args:
        title: 错误标题。
        message: 面向用户展示的错误说明。

    Returns:
        UTF-8 编码的 HTML 字节串。
    """
    return (
        "<!doctype html>"
        "<html lang='en'>"
        "<head><meta charset='utf-8'><title>{title}</title></head>"
        "<body><main><h1>{title}</h1><p>{message}</p></main></body>"
        "</html>"
    ).format(title=title, message=message).encode("utf-8")


def create_web_app() -> Callable:
    """创建保守的 legacy WSGI 应用。

    Returns:
        WSGI callable；仅保留健康检查，Dashboard 页面/API 已移除。
    """

    def app(environ, start_response):
        """处理 legacy WSGI 请求。

        Args:
            environ: WSGI 环境变量。
            start_response: WSGI 响应启动回调。

        Returns:
            包含响应体的可迭代对象。
        """
        path = str(environ.get("PATH_INFO") or "/")
        if path == "/healthz":
            body = b'{"status":"ok"}'
            start_response(
                f"{HTTPStatus.OK.value} {HTTPStatus.OK.phrase}",
                [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))],
            )
            return [body]

        body = render_error_html("Page not found", "The legacy dashboard route has been removed.")
        start_response(
            f"{HTTPStatus.NOT_FOUND.value} {HTTPStatus.NOT_FOUND.phrase}",
            [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))],
        )
        return [body]

    return app
