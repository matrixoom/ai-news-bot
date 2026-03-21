"""WSGI compatibility app and shared rendering helpers for the dashboard shell."""
import json
from dataclasses import asdict
from html import escape
from typing import Callable, Iterable, Tuple

from ...services.dashboard_service import DashboardService, DashboardSnapshot


def build_dashboard_payload(snapshot: DashboardSnapshot) -> dict:
    """Convert the dashboard snapshot into a JSON-serializable payload."""
    return asdict(snapshot)


DISPLAY_TEXT = {
    "live": "正常",
    "degraded": "降级",
    "sample": "样例",
    "compatible": "兼容",
    "unknown": "未知",
    "unavailable": "不可用",
    "breakout": "突破",
    "constructive": "偏强",
    "neutral": "中性",
    "pressured": "承压",
    "high": "高",
    "medium": "中",
    "low": "低",
    "monthly": "月度",
    "quarterly": "季度",
    "yearly": "年度",
    "up": "上行",
    "down": "下行",
    "flat": "持平",
    "rss": "RSS",
    "search": "搜索",
}


def _display_text(value: str) -> str:
    return DISPLAY_TEXT.get(value, value)


def _render_badge(text: str) -> str:
    return f"<span class=\"badge\">{escape(_display_text(text))}</span>"


def render_dashboard_html(snapshot: DashboardSnapshot) -> bytes:
    """Render the dashboard shell as server-side HTML."""
    payload = build_dashboard_payload(snapshot)
    summary = payload["dashboard_summary"]

    news_columns = "".join(
        (
            "<section class=\"card section-card\">"
            f"<div class=\"section-head\"><h2>{escape(section['title'])}</h2>{_render_badge(section['status'])}</div>"
            f"<p class=\"muted\">{escape(section['description'])}</p>"
            "<ul class=\"news-list\">"
            + "".join(
                (
                    "<li>"
                    + (
                        f"<strong><a href=\"{escape(item.get('url', '#'))}\" target=\"_blank\" rel=\"noreferrer\">{escape(item['title'])}</a></strong>"
                        if item.get("url")
                        else f"<strong>{escape(item['title'])}</strong>"
                    )
                    + f"<span>{escape(item['source'])}</span>"
                    + f"<span>{escape(item['published_at'])}</span>"
                    + f"<em>{escape(item['tag'])}</em>"
                    "</li>"
                )
                for item in section["items"]
            )
            + "</ul></section>"
        )
        for section in payload["news_sections"]
    )

    macro_cards = "".join(
        (
            "<article class=\"card metric-card\">"
            f"<div class=\"section-head\"><h3>{escape(card['label'])}</h3>{_render_badge(card['status'])}</div>"
            f"<p class=\"metric-value\">{escape(card['value'])}</p>"
            f"<p class=\"muted\">前值：{escape(card.get('previous_value', '暂无数据'))}</p>"
            f"<p class=\"muted\">{escape(card.get('change_label', '暂无变化信息'))}</p>"
            f"<p class=\"signal\">趋势：{escape(_display_text(card.get('trend', 'unavailable')))}</p>"
            f"<p class=\"muted\">来源：{escape(card.get('source_label', '暂无数据'))}</p>"
            f"<p class=\"muted\">更新时间：{escape(card.get('updated_at', '暂无数据'))} | 频率：{escape(_display_text(card.get('frequency', 'unavailable')))}</p>"
            f"<p class=\"muted\">{escape(card['context'])}</p>"
            "</article>"
        )
        for card in payload["macro_sections"]
    )

    market_cards = "".join(
        (
            "<article class=\"card market-card\">"
            f"<div class=\"section-head\"><h3>{escape(card['label'])}</h3>{_render_badge(card['status'])}</div>"
            f"<p class=\"metric-value\">收盘：{escape(card['close_value'])}</p>"
            f"<p class=\"muted\">MA20：{escape(card['ma20_value'])}</p>"
            f"<p class=\"signal\">状态：{escape(_display_text(card['signal']))}</p>"
            f"<p class=\"muted\">偏离：{escape(card.get('deviation_pct', '暂无数据'))}</p>"
            f"<p class=\"muted\">交易日：{escape(card.get('trade_date', '暂无数据'))}</p>"
            f"<p class=\"muted\">来源：{escape(card.get('source_label', '暂无数据'))}</p>"
            f"<p class=\"muted\">{escape(card.get('explanation', '暂无数据'))}</p>"
            "</article>"
        )
        for card in payload["market_sections"]
    )

    event_groups = "".join(
        (
            "<section class=\"card section-card\">"
            f"<div class=\"section-head\"><h3>{escape(group['title'])}</h3>{_render_badge(group['status'])}</div>"
            "<ul class=\"event-list\">"
            + "".join(
                (
                    "<li>"
                    f"<strong>{escape(item['title'])}</strong>"
                    f"<span>{escape(item['time_window'])}</span>"
                    f"<span>{escape(_display_text(item['confidence']))}</span>"
                    f"<em>{escape(item['source'])}</em>"
                    "</li>"
                )
                for item in group["items"]
            )
            + "</ul></section>"
        )
        for group in payload["event_sections"]
    )

    status_items = "".join(
        (
            "<li class=\"status-item\">"
            f"<strong>{escape(item['label'])}</strong>"
            f"{_render_badge(item['status'])}"
            f"<span>{escape(item['detail'])}</span>"
            "</li>"
        )
        for item in payload["data_status"]
    )

    highlights = "".join(f"<li>{escape(item)}</li>" for item in summary["highlights"])

    html = f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <title>{escape(snapshot.title)}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      :root {{
        --bg: #f4efe6;
        --panel: rgba(255, 252, 247, 0.88);
        --ink: #16212f;
        --muted: #53606f;
        --line: rgba(22, 33, 47, 0.12);
        --accent: #a14d2a;
        --accent-soft: #f1dacd;
        --ok: #2f6b4f;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: "Trebuchet MS", "Segoe UI", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(161, 77, 42, 0.18), transparent 28%),
          linear-gradient(160deg, #f7f0e4 0%, #efe5d3 100%);
      }}
      main {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 32px 20px 56px;
      }}
      .hero {{
        background: linear-gradient(135deg, rgba(255,255,255,0.72), rgba(255,255,255,0.52));
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 28px;
        backdrop-filter: blur(10px);
        box-shadow: 0 16px 40px rgba(40, 34, 25, 0.08);
      }}
      h1, h2, h3 {{
        font-family: Georgia, "Times New Roman", serif;
        margin: 0;
      }}
      h1 {{
        font-size: clamp(2rem, 4vw, 3.4rem);
        line-height: 1;
        margin-bottom: 12px;
      }}
      p, li, span, em {{ line-height: 1.5; }}
      .muted {{ color: var(--muted); }}
      .highlights {{
        margin: 18px 0 0;
        padding-left: 20px;
      }}
      .badge {{
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 999px;
        background: var(--accent-soft);
        color: var(--accent);
        font-size: 0.78rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
      }}
      .section-head {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 10px;
      }}
      .grid {{
        display: grid;
        gap: 18px;
        margin-top: 20px;
      }}
      .grid-3 {{
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      }}
      .grid-2 {{
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      }}
      .card {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 10px 30px rgba(40, 34, 25, 0.06);
      }}
      .news-list, .event-list, .status-list {{
        list-style: none;
        margin: 0;
        padding: 0;
      }}
      .news-list li, .event-list li, .status-item {{
        display: grid;
        gap: 4px;
        padding: 12px 0;
        border-top: 1px solid var(--line);
      }}
      .news-list li:first-child, .event-list li:first-child {{
        border-top: 0;
        padding-top: 0;
      }}
      .metric-value {{
        font-size: 1.65rem;
        font-weight: 700;
        margin: 8px 0 6px;
      }}
      .signal {{
        color: var(--ok);
        font-weight: 700;
        margin: 10px 0 0;
      }}
      .footer-links {{
        display: flex;
        gap: 14px;
        flex-wrap: wrap;
        margin-top: 20px;
      }}
      a {{
        color: var(--accent);
        text-decoration: none;
      }}
      a:hover {{
        text-decoration: underline;
      }}
      @media (max-width: 720px) {{
        main {{
          padding: 18px 14px 42px;
        }}
        .hero, .card {{
          padding: 18px;
          border-radius: 18px;
        }}
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <p class="muted">仪表盘总览</p>
        <h1>{escape(summary['title'])}</h1>
        <p>{escape(summary['subtitle'])}</p>
        <p class="muted">更新时间 {escape(summary['as_of_label'])}</p>
        <p>{escape(summary['coverage_note'])}</p>
        <ul class="highlights">{highlights}</ul>
        <div class="footer-links">
          <a href="/api/dashboard">结构化 API</a>
          <a href="/healthz">健康检查</a>
        </div>
      </section>
      <section class="grid grid-3">{news_columns}</section>
      <section class="grid grid-3">{macro_cards}</section>
      <section class="grid grid-2">{market_cards}</section>
      <section class="grid grid-2">{event_groups}</section>
      <section class="card">
        <div class="section-head">
          <h2>数据状态</h2>
          {_render_badge("兼容")}
        </div>
        <ul class="status-list">{status_items}</ul>
      </section>
    </main>
  </body>
</html>
"""
    return html.encode("utf-8")


def render_error_html(title: str, message: str) -> bytes:
    """Render a compact error page that matches the dashboard style."""
    html = f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <title>{escape(title)}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
  </head>
  <body style="margin:0;font-family:Trebuchet MS,Segoe UI,sans-serif;background:#f4efe6;color:#16212f;">
    <main style="max-width:760px;margin:0 auto;padding:48px 20px;">
      <section style="background:#fffaf5;border:1px solid rgba(22,33,47,.12);border-radius:20px;padding:28px;">
        <p style="margin:0 0 10px;color:#a14d2a;text-transform:uppercase;font-size:12px;">仪表盘</p>
        <h1 style="margin:0 0 12px;font-family:Georgia,Times New Roman,serif;">{escape(title)}</h1>
        <p style="margin:0 0 18px;">{escape(message)}</p>
        <a href="/" style="color:#a14d2a;">返回首页</a>
      </section>
    </main>
  </body>
</html>
"""
    return html.encode("utf-8")


def _response(status: str, body: bytes, content_type: str) -> Tuple[str, list, Iterable[bytes]]:
    headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(body))),
    ]
    return status, headers, [body]


def create_web_app(dashboard_service: DashboardService | None = None) -> Callable:
    """Create a WSGI-compatible app for compatibility tests and simple hosting."""
    service = dashboard_service or DashboardService()

    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/")

        try:
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
                payload = json.dumps(build_dashboard_payload(snapshot), ensure_ascii=True).encode("utf-8")
                status, headers, body = _response(
                    "200 OK",
                    payload,
                    "application/json; charset=utf-8",
                )
                start_response(status, headers)
                return body

            if path == "/":
                snapshot = service.build_snapshot()
                status, headers, body = _response(
                    "200 OK",
                    render_dashboard_html(snapshot),
                    "text/html; charset=utf-8",
                )
                start_response(status, headers)
                return body

            status, headers, body = _response(
                "404 Not Found",
                render_error_html("页面不存在", "请求的仪表盘路由不存在。"),
                "text/html; charset=utf-8",
            )
            start_response(status, headers)
            return body

        except Exception:
            status, headers, body = _response(
                "503 Service Unavailable",
                render_error_html("仪表盘暂不可用", "当前无法构建仪表盘视图模型。"),
                "text/html; charset=utf-8",
            )
            start_response(status, headers)
            return body

    return app
