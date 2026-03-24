"""Build unified push reports from the dashboard snapshot."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta
from html import escape
import math

from .dashboard_service import DashboardSnapshot


class PushReportService:
    """Render dashboard data into reusable markdown and HTML push reports."""

    def build_subject(
        self,
        snapshot: DashboardSnapshot,
        language: str = "en",
        *,
        module_ids: Iterable[str] | None = None,
    ) -> str:
        _ = module_ids
        suffix = f" [{language.upper()}]" if language != "en" else ""
        return f"{snapshot.title} - {snapshot.generated_at[:10]}{suffix}"

    def build_markdown(
        self,
        snapshot: DashboardSnapshot,
        language: str = "en",
        *,
        module_ids: Iterable[str] | None = None,
    ) -> str:
        _ = language
        selected = self._selected_modules(module_ids)
        lines: list[str] = [
            f"# {snapshot.title}",
            "",
            f"生成时间: {snapshot.generated_at}",
            "",
        ]

        if "news" in selected:
            lines.append("## 新闻")
            for section in snapshot.news_sections:
                lines.append(f"### {section.title}")
                for item in section.items:
                    lines.append(f"- {item.title} | {item.source} | {item.published_at} | {item.tag}")
                lines.append("")

        if "macro" in selected:
            lines.extend(
                [
                    "## 宏观指标",
                    "",
                    "| 指标 | 当前值 | 前值 | 趋势 | 更新时间 |",
                    "| --- | --- | --- | --- | --- |",
                ]
            )
            for card in snapshot.macro_sections:
                lines.append(
                    f"| {card.label} | {card.value} | {card.previous_value} | {card.trend} | {card.updated_at} |"
                )
            lines.append("")

        if "market" in selected:
            lines.extend(
                [
                    "## 市场模型",
                    "",
                    "| 指数 | 收盘 | MA20 | 偏离 | 信号 |",
                    "| --- | --- | --- | --- | --- |",
                ]
            )
            for card in snapshot.market_sections:
                lines.append(
                    f"| {card.label} | {card.close_value} | {card.ma20_value} | {card.deviation_pct} | {card.signal} |"
                )
            lines.extend(
                [
                    "",
                    "### 近3个月趋势",
                    "",
                    "| 指数 | 区间涨跌 | 区间高低 | 最新收盘 |",
                    "| --- | --- | --- | --- |",
                ]
            )
            for card in snapshot.market_sections:
                trend = self._build_market_trend_summary(card)
                lines.append(
                    f"| {card.label} | {trend['change_label']} | {trend['range_label']} | {trend['latest_label']} |"
                )
            lines.append("")

        if "events" in selected:
            lines.extend(["## 事件展望", ""])
            for section in snapshot.event_sections:
                lines.append(f"### {section.title}")
                for item in section.items:
                    lines.append(f"- {item.title} | {item.time_window} | {item.confidence} | {item.source}")
                lines.append("")

        lines.extend(["## 数据状态", ""])
        for item in snapshot.data_status:
            lines.append(f"- {item.label}: {item.status} - {item.detail}")

        return "\n".join(lines)

    def build_email_html(
        self,
        snapshot: DashboardSnapshot,
        *,
        module_ids: Iterable[str] | None = None,
        layout: str = "newspaper",
    ) -> str:
        selected = self._selected_modules(module_ids)
        if layout == "briefing":
            body = self._build_briefing_body(snapshot, selected)
        else:
            body = self._build_newspaper_body(snapshot, selected)
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{escape(snapshot.title)}</title>
  </head>
  <body style="margin:0;padding:0;background:#f3efe6;color:#171717;">
    <div style="max-width:1120px;margin:0 auto;padding:28px 18px 40px;font-family:Georgia,'Times New Roman','Songti SC','STSong',serif;">
      {body}
    </div>
  </body>
</html>"""

    def _build_newspaper_body(self, snapshot: DashboardSnapshot, selected: set[str]) -> str:
        header = f"""
<header style="padding:0 0 18px;border-bottom:3px double #171717;">
  <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-end;flex-wrap:wrap;">
    <div>
      <div style="font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:#7a6b4d;">Finance Dispatch</div>
      <h1 style="margin:4px 0 0;font-size:34px;line-height:1.05;">{escape(snapshot.title)}</h1>
    </div>
    <div style="font-size:13px;color:#4f4a40;text-align:right;">
      <div>Edition: {escape(snapshot.generated_at[:10])}</div>
      <div>Generated: {escape(snapshot.generated_at)}</div>
    </div>
  </div>
</header>"""
        lead = f"""
<section style="padding:14px 0 18px;border-bottom:1px solid #b8aa8c;">
  <p style="margin:0;font-size:15px;line-height:1.8;color:#2d2a24;">{escape(snapshot.summary)}</p>
</section>"""

        columns: list[str] = []
        if "market" in selected:
            columns.append(self._build_market_column(snapshot))
        if "macro" in selected:
            columns.append(self._build_macro_column(snapshot))
        if "news" in selected:
            columns.append(self._build_news_column(snapshot))
        if "events" in selected:
            columns.append(self._build_events_column(snapshot))
        if not columns:
            columns.append("<section><p>暂无可推送内容。</p></section>")

        return f"""{header}
{lead}
<main style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px;padding-top:18px;">
  {''.join(columns)}
</main>"""

    def _build_briefing_body(self, snapshot: DashboardSnapshot, selected: set[str]) -> str:
        sections: list[str] = [
            f"""
<header style="padding:0 0 16px;border-bottom:2px solid #171717;">
  <h1 style="margin:0;font-size:30px;line-height:1.05;">{escape(snapshot.title)}</h1>
  <p style="margin:8px 0 0;font-size:14px;color:#4f4a40;">生成时间: {escape(snapshot.generated_at)}</p>
</header>"""
        ]
        if "market" in selected:
            sections.append(self._build_market_column(snapshot))
        if "macro" in selected:
            sections.append(self._build_macro_column(snapshot))
        if "news" in selected:
            sections.append(self._build_news_column(snapshot))
        if "events" in selected:
            sections.append(self._build_events_column(snapshot))
        return "".join(sections)

    def _build_market_column(self, snapshot: DashboardSnapshot) -> str:
        summary_rows = "".join(
            f"""
<tr>
  <td style="padding:10px 0;border-top:1px solid #d0c3a8;font-weight:700;">{escape(card.label)}</td>
  <td style="padding:10px 0;border-top:1px solid #d0c3a8;text-align:right;">{escape(card.close_value)}</td>
  <td style="padding:10px 0;border-top:1px solid #d0c3a8;text-align:right;">{escape(card.ma20_value)}</td>
  <td style="padding:10px 0;border-top:1px solid #d0c3a8;text-align:right;">{escape(card.deviation_pct)}</td>
  <td style="padding:10px 0;border-top:1px solid #d0c3a8;text-align:right;letter-spacing:0.08em;text-transform:uppercase;color:#8b5e00;">{escape(card.signal)}</td>
</tr>"""
            for card in snapshot.market_sections
        )
        trend_cards = "".join(self._build_market_trend_block(card) for card in snapshot.market_sections)
        return f"""
<section style="padding:0 14px 16px;border:1px solid #cdbf9d;background:#faf6eb;">
  <div style="padding:14px 0 10px;border-bottom:2px solid #171717;">
    <div style="font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#7a6b4d;">Market Models</div>
    <h2 style="margin:4px 0 0;font-size:24px;">市场日报</h2>
  </div>
  <div style="padding-top:14px;">
    <div style="font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#7a6b4d;">Fishbowl Summary</div>
    <table style="width:100%;border-collapse:collapse;font-size:14px;margin-top:10px;">
      <thead>
        <tr>
          <th style="padding:0 0 10px;text-align:left;border-bottom:1px solid #171717;">指数</th>
          <th style="padding:0 0 10px;text-align:right;border-bottom:1px solid #171717;">收盘</th>
          <th style="padding:0 0 10px;text-align:right;border-bottom:1px solid #171717;">MA20</th>
          <th style="padding:0 0 10px;text-align:right;border-bottom:1px solid #171717;">偏离</th>
          <th style="padding:0 0 10px;text-align:right;border-bottom:1px solid #171717;">信号</th>
        </tr>
      </thead>
      <tbody>{summary_rows or '<tr><td colspan="5" style="padding-top:10px;">暂无市场模型数据。</td></tr>'}</tbody>
    </table>
  </div>
  <div style="padding-top:18px;">
    <div style="display:flex;justify-content:space-between;gap:12px;align-items:baseline;flex-wrap:wrap;">
      <div style="font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#7a6b4d;">3M Trend</div>
      <div style="font-size:12px;color:#6e654f;">近3个月收盘走势、区间涨跌与高低点</div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:10px;align-items:start;">
      {trend_cards or '<p style="margin:0;">暂无趋势数据。</p>'}
    </div>
  </div>
</section>"""

    def _build_market_trend_block(self, card) -> str:
        trend = self._build_market_trend_summary(card)
        return f"""
<article style="padding:12px;border:1px solid #d0c3a8;background:#fffdf7;">
  <div style="display:flex;justify-content:space-between;gap:12px;align-items:baseline;flex-wrap:wrap;">
    <h3 style="margin:0;font-size:18px;">{escape(card.label)}</h3>
    <span style="font-size:12px;letter-spacing:0.12em;text-transform:uppercase;color:#8b5e00;">{escape(card.signal)}</span>
  </div>
  <div style="margin-top:8px;font-size:12px;color:#6e654f;">组合图与市场模型保持一致，展示 Close、M20 与 Deviation。</div>
  <div style="margin-top:10px;">{self._render_market_combo_chart(trend["chart_points"], label=card.label)}</div>
  <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:10px;font-size:13px;">
    <div><strong>3M 涨跌</strong><br />{escape(trend["change_label"])}</div>
    <div><strong>区间高低</strong><br />{escape(trend["range_label"])}</div>
    <div><strong>最新收盘</strong><br />{escape(trend["latest_label"])}</div>
    <div><strong>交易日</strong><br />{escape(card.trade_date)}</div>
  </div>
  <p style="margin:10px 0 0;font-size:13px;line-height:1.7;color:#4f4a40;">{escape(card.explanation)}</p>
</article>"""

    def _build_market_trend_summary(self, card) -> dict[str, object]:
        chart_points = self._normalize_market_chart_points(self._extract_recent_market_points(card))
        closes = [point["close_price"] for point in chart_points]
        if not closes:
            return {
                "chart_points": [],
                "change_label": "暂无数据",
                "range_label": "暂无数据",
                "latest_label": card.close_value,
            }
        start = closes[0]
        latest = closes[-1]
        highest = max(closes)
        lowest = min(closes)
        change_label = "暂无数据" if not start else f"{((latest - start) / start) * 100:+.1f}%"
        return {
            "chart_points": chart_points,
            "change_label": change_label,
            "range_label": f"{lowest:.1f} - {highest:.1f}",
            "latest_label": f"{latest:.1f}",
        }

    def _extract_recent_market_points(self, card) -> list[dict]:
        raw_points = list(getattr(card, "chart_points", []) or [])
        dated_points: list[tuple[date, dict]] = []
        for point in raw_points:
            try:
                trade_date = datetime.strptime(str(point.get("trade_date")), "%Y-%m-%d").date()
            except (TypeError, ValueError):
                continue
            dated_points.append((trade_date, point))
        if not dated_points:
            return []
        dated_points.sort(key=lambda item: item[0])
        latest_date = dated_points[-1][0]
        threshold = latest_date - timedelta(days=92)
        filtered = [point for trade_date, point in dated_points if trade_date >= threshold]
        return filtered or [point for _, point in dated_points[-65:]]

    def _normalize_market_chart_points(self, points: list[dict]) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        for point in points:
            close_price = point.get("close_price")
            if not isinstance(close_price, (int, float)):
                continue
            ma20_price = point.get("ma20_price")
            deviation_pct = point.get("deviation_pct")
            normalized.append(
                {
                    "trade_date": str(point.get("trade_date") or ""),
                    "close_price": float(close_price),
                    "ma20_price": float(ma20_price) if isinstance(ma20_price, (int, float)) else None,
                    "deviation_pct": float(deviation_pct) if isinstance(deviation_pct, (int, float)) else None,
                }
            )
        return normalized

    def _render_market_combo_chart(self, points: list[dict[str, object]], *, label: str) -> str:
        if len(points) < 2:
            return '<div style="height:112px;display:grid;place-items:center;border:1px dashed #d0c3a8;color:#6e654f;">暂无趋势数据</div>'

        width = 344.0
        height = 126.0
        left = 14.0
        right = 14.0
        top = 12.0
        price_height = 66.0
        gap = 10.0
        deviation_height = 24.0
        chart_width = width - left - right
        zero_y = top + price_height + gap + (deviation_height / 2)
        deviation_center = deviation_height / 2

        price_values = [
            value
            for point in points
            for value in (point["close_price"], point["ma20_price"])
            if isinstance(value, (int, float))
        ]
        min_price = min(price_values)
        max_price = max(price_values)
        if math.isclose(max_price, min_price):
            max_price += 1
            min_price -= 1

        deviation_values = [
            float(point["deviation_pct"])
            for point in points
            if isinstance(point.get("deviation_pct"), (int, float))
        ]
        max_abs_deviation = max((abs(value) for value in deviation_values), default=1.0)
        if math.isclose(max_abs_deviation, 0.0):
            max_abs_deviation = 1.0

        def to_x(index: int) -> float:
            return left + (chart_width * index) / max(len(points) - 1, 1)

        def to_price_y(value: float) -> float:
            return top + ((max_price - value) / (max_price - min_price)) * price_height

        def to_deviation_y(value: float) -> float:
            return zero_y - (value / max_abs_deviation) * deviation_center

        close_path = self._build_svg_line_path(
            [(to_x(index), to_price_y(float(point["close_price"]))) for index, point in enumerate(points)]
        )
        ma20_path = self._build_svg_line_path(
            [
                (
                    to_x(index),
                    to_price_y(float(point["ma20_price"])) if isinstance(point.get("ma20_price"), (int, float)) else None,
                )
                for index, point in enumerate(points)
            ]
        )

        step = chart_width / max(len(points) - 1, 1)
        bar_width = min(8.0, max(3.0, step * 0.55))
        bars: list[str] = []
        for index, point in enumerate(points):
            value = point.get("deviation_pct")
            if not isinstance(value, (int, float)):
                continue
            x = to_x(index) - (bar_width / 2)
            y = to_deviation_y(float(value))
            bar_top = min(y, zero_y)
            bar_height = max(abs(zero_y - y), 1.0)
            fill = "#ff5f72" if value > 0 else "#37c48d" if value < 0 else "#8fa0b4"
            bars.append(
                f'<rect x="{x:.2f}" y="{bar_top:.2f}" width="{bar_width:.2f}" '
                f'height="{bar_height:.2f}" rx="1.5" fill="{fill}"></rect>'
            )

        last_close_x = to_x(len(points) - 1)
        last_close_y = to_price_y(float(points[-1]["close_price"]))
        last_ma20_value = next(
            (float(point["ma20_price"]) for point in reversed(points) if isinstance(point.get("ma20_price"), (int, float))),
            None,
        )
        last_ma20_y = to_price_y(last_ma20_value) if last_ma20_value is not None else None
        first_date = str(points[0].get("trade_date") or "")
        last_date = str(points[-1].get("trade_date") or "")

        return f"""
<div>
  <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:12px;color:#6e654f;margin-bottom:6px;">
    <span><span style="display:inline-block;width:12px;height:2px;background:#f6a313;vertical-align:middle;margin-right:6px;"></span>Close</span>
    <span><span style="display:inline-block;width:12px;height:0;border-top:2px dashed #31b8c4;vertical-align:middle;margin-right:6px;"></span>M20</span>
    <span><span style="display:inline-block;width:10px;height:10px;background:#ff5f72;vertical-align:middle;margin-right:6px;"></span>Deviation</span>
  </div>
  <svg viewBox="0 0 {width:.0f} {height:.0f}" width="100%" height="{height:.0f}" role="img" aria-label="{escape(label)} 近3个月组合趋势图">
    <line x1="{left:.2f}" y1="{top:.2f}" x2="{width - right:.2f}" y2="{top:.2f}" stroke="#e2d7c0" stroke-width="1"></line>
    <line x1="{left:.2f}" y1="{top + (price_height / 2):.2f}" x2="{width - right:.2f}" y2="{top + (price_height / 2):.2f}" stroke="#efe6d3" stroke-width="1" stroke-dasharray="3 3"></line>
    <line x1="{left:.2f}" y1="{top + price_height:.2f}" x2="{width - right:.2f}" y2="{top + price_height:.2f}" stroke="#e2d7c0" stroke-width="1"></line>
    <line x1="{left:.2f}" y1="{zero_y:.2f}" x2="{width - right:.2f}" y2="{zero_y:.2f}" stroke="#d0c3a8" stroke-width="1" stroke-dasharray="4 4"></line>
    {''.join(bars)}
    <path d="{close_path}" fill="none" stroke="#f6a313" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path>
    <path d="{ma20_path}" fill="none" stroke="#31b8c4" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="6 4"></path>
    <circle cx="{last_close_x:.2f}" cy="{last_close_y:.2f}" r="3.2" fill="#f6a313"></circle>
    {f'<circle cx="{last_close_x:.2f}" cy="{last_ma20_y:.2f}" r="2.8" fill="#31b8c4"></circle>' if last_ma20_y is not None else ''}
  </svg>
  <div style="display:flex;justify-content:space-between;gap:12px;margin-top:6px;font-size:11px;color:#6e654f;">
    <span>{escape(first_date)}</span>
    <span>{escape(last_date)}</span>
  </div>
</div>"""

    def _build_svg_line_path(self, points: list[tuple[float, float | None]]) -> str:
        commands: list[str] = []
        started = False
        for x, y in points:
            if y is None:
                started = False
                continue
            commands.append(f"{'M' if not started else 'L'} {x:.2f} {y:.2f}")
            started = True
        return " ".join(commands)

    def _build_macro_column(self, snapshot: DashboardSnapshot) -> str:
        rows = "".join(
            f"""
<tr>
  <td style="padding:8px 0;border-top:1px solid #d0c3a8;">{escape(card.label)}</td>
  <td style="padding:8px 0;border-top:1px solid #d0c3a8;text-align:right;">{escape(card.value)}</td>
</tr>"""
            for card in snapshot.macro_sections
        )
        return f"""
<section style="padding:0 14px 16px;border:1px solid #cdbf9d;background:#fffdf7;">
  <div style="padding:14px 0 10px;border-bottom:2px solid #171717;">
    <div style="font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#7a6b4d;">Macro Monitor</div>
    <h2 style="margin:4px 0 0;font-size:24px;">宏观摘要</h2>
  </div>
  <table style="width:100%;border-collapse:collapse;font-size:14px;">
    <tbody>{rows or '<tr><td style="padding-top:10px;">暂无宏观数据。</td><td></td></tr>'}</tbody>
  </table>
</section>"""

    def _build_news_column(self, snapshot: DashboardSnapshot) -> str:
        items = []
        for section in snapshot.news_sections:
            items.append(
                f"""
<div style="padding-top:12px;border-top:1px solid #d0c3a8;">
  <h3 style="margin:0 0 8px;font-size:18px;">{escape(section.title)}</h3>
  {''.join(
      f"<p style='margin:0 0 8px;font-size:14px;line-height:1.7;'><strong>{escape(item.title)}</strong><br /><span style='color:#4f4a40;'>{escape(item.source)} | {escape(item.published_at)}</span></p>"
      for item in section.items[:4]
  ) or '<p style=\"margin:0;\">暂无新闻。</p>'}
</div>"""
            )
        return f"""
<section style="padding:0 14px 16px;border:1px solid #cdbf9d;background:#fffdf7;">
  <div style="padding:14px 0 10px;border-bottom:2px solid #171717;">
    <div style="font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#7a6b4d;">Headlines</div>
    <h2 style="margin:4px 0 0;font-size:24px;">新闻线索</h2>
  </div>
  {''.join(items) or '<p style="margin:14px 0 0;">暂无新闻数据。</p>'}
</section>"""

    def _build_events_column(self, snapshot: DashboardSnapshot) -> str:
        items = []
        for section in snapshot.event_sections:
            rows = "".join(
                f"<li style='margin:0 0 8px;line-height:1.7;'><strong>{escape(item.title)}</strong> | {escape(item.expected_date)} | {escape(item.region)}</li>"
                for item in section.items[:5]
            )
            items.append(
                f"""
<div style="padding-top:12px;border-top:1px solid #d0c3a8;">
  <h3 style="margin:0 0 8px;font-size:18px;">{escape(section.title)}</h3>
  <ul style="margin:0;padding-left:18px;font-size:14px;">{rows or '<li>暂无事件。</li>'}</ul>
</div>"""
            )
        return f"""
<section style="padding:0 14px 16px;border:1px solid #cdbf9d;background:#faf6eb;">
  <div style="padding:14px 0 10px;border-bottom:2px solid #171717;">
    <div style="font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#7a6b4d;">Events</div>
    <h2 style="margin:4px 0 0;font-size:24px;">事件展望</h2>
  </div>
  {''.join(items) or '<p style="margin:14px 0 0;">暂无事件数据。</p>'}
</section>"""

    def _selected_modules(self, module_ids: Iterable[str] | None) -> set[str]:
        allowed = {"news", "macro", "market", "events"}
        if module_ids is None:
            return allowed
        selected = {str(module_id).strip() for module_id in module_ids if str(module_id).strip() in allowed}
        return selected or {"market"}
