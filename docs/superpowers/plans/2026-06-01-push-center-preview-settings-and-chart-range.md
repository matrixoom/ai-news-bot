# Push Center Preview Settings And Chart Range Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Push Center 的 Schedules 页面改为全宽日报预览和设置弹窗，并让宽基指数图表支持持久化的 `3m | 6m | 1y | 2y | 3y` 时间范围，默认推送近一年数据。

**Architecture:** 新增一个后端共享范围模型，作为配置校验、报告裁剪和市场刷新窗口的唯一来源。Push Center 配置新增 `market_chart_range`；预览支持“仅用本地历史重绘”和“主动刷新后重绘”两种语义；全量刷新按当前草稿范围抓取并只做 SQLite `upsert`。前端把所有编辑表单收进弹窗，预览卡片承载范围下拉框和四个 Heroicons 图标按钮。

**Tech Stack:** Python 3.12、FastAPI、SQLite、pytest、TypeScript、React 18、TanStack Query、Tailwind CSS、Heroicons、Vitest、Testing Library。

---

## File Structure

### Backend

- Create: `src/services/push_market_chart_range.py`
  - 定义五档范围、默认值、严格校验和展示文案。
- Modify: `src/services/push_center_service.py`
  - 持久化范围；把范围传给报告、手动发送、定时发送和全量刷新；校验预览复用范围。
- Modify: `src/services/push_report_service.py`
  - 按范围裁剪点位，并动态渲染 Markdown、HTML、指标文案和 SVG `aria-label`。
- Modify: `src/services/dashboard_service.py`
  - 把刷新窗口传给市场监控服务，并按窗口隔离市场模块缓存。
- Modify: `src/services/market_monitoring_service.py`
  - 按请求窗口加载和刷新历史；移除删除最近窗口的产品调用。
- Modify: `src/services/market_history_store.py`
  - 移除 `replace_from` 删除能力，仅保留按日期 `upsert`。
- Modify: `src/providers/contracts.py`
  - 给宽基指数 provider 合同增加 `history_window_days`。
- Modify: `src/providers/live_data.py`
  - 实时和 fallback provider 按请求窗口拉取和转发历史。
- Modify: `src/providers/sample_data.py`
  - 样例 provider 按请求窗口生成离线历史。
- Modify: `src/app/web/fastapi_app.py`
  - 更新 Push 预览和刷新接口注释，保持错误响应契约。
- Modify: `.data/push_center.json.template`
- Modify: `.data/push_center.template.json`
  - 模板增加默认 `market_chart_range: "1y"`。

### Frontend

- Modify: `frontend/src/features/push/model/push-module.types.ts`
  - 增加范围类型、选项、配置字段和预览字段。
- Modify: `frontend/src/features/push/model/push-module-adapter.ts`
  - 适配 snake_case/camelCase 字段，旧 payload 默认 `1y`。
- Modify: `frontend/src/features/push/api/preview-push.ts`
  - 增加 `refreshData` 参数。
- Modify: `frontend/src/features/push/components/push-config-form.tsx`
  - 仅保留编辑和保存。
- Create: `frontend/src/features/push/components/push-flash-message.tsx`
  - 复用操作结果提示。
- Create: `frontend/src/features/push/components/push-settings-dialog.tsx`
  - 组合计划任务编辑器和投递配置表单。
- Modify: `frontend/src/features/push/components/push-preview-panel.tsx`
  - 增加范围下拉和四个图标按钮。
- Modify: `frontend/src/pages/push-page.tsx`
  - Schedules 页面全宽预览；管理弹窗和轻量重绘。
- Modify: `frontend/src/app/__tests__/workbench-api-mocks.ts`
  - mock 新配置字段、预览字段和 `refresh_data`。

### Tests And Docs

- Modify: `tests/test_push_center_api.py`
- Modify: `tests/test_push_workflow.py`
- Modify: `tests/test_market_data_module.py`
- Modify: `frontend/src/features/push/__tests__/push-page.test.tsx`
- Modify: `frontend/src/features/push/__tests__/push-preview-panel.test.tsx`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/api-contract.md`
- Modify: `docs/test-strategy.md`

## Task 1: Add Shared Range Model And Push Config Contract

**Files:**
- Create: `src/services/push_market_chart_range.py`
- Modify: `src/services/push_center_service.py:89-115`
- Modify: `src/services/push_center_service.py:574-619`
- Modify: `src/services/push_center_service.py:844-936`
- Modify: `.data/push_center.json.template`
- Modify: `.data/push_center.template.json`
- Test: `tests/test_push_center_api.py`

- [ ] **Step 1: Write failing backend config tests**

Add these tests to `PushCenterModuleTests`:

```python
    def test_push_config_defaults_market_chart_range_to_one_year(self):
        """校验旧配置缺少范围字段时自动兼容为近一年。"""
        payload = self.client.get("/api/frontend/modules/push").json()

        config = payload["module"]["details"][0]["section"]["config"]

        self.assertEqual(config["market_chart_range"], "1y")

    def test_push_config_persists_market_chart_range(self):
        """校验合法范围会写入配置文件并返回给前端。"""
        response = self.client.put(
            "/api/push/config",
            json={"config": {"market_chart_range": "3y"}},
        )

        self.assertEqual(response.status_code, 200)
        saved = self._read_json(self.config_path)
        self.assertEqual(saved["market_chart_range"], "3y")

    def test_push_config_rejects_invalid_market_chart_range(self):
        """校验非法范围快速失败，避免静默回退到错误推送区间。"""
        response = self.client.put(
            "/api/push/config",
            json={"config": {"market_chart_range": "5y"}},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "push_config_update_failed"})
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
uv run python -m pytest tests/test_push_center_api.py -k "market_chart_range" -q
```

Expected: FAIL because `market_chart_range` is absent and invalid values are not rejected.

- [ ] **Step 3: Create the shared range model**

Create `src/services/push_market_chart_range.py`:

```python
"""Push Center 宽基指数图表时间范围定义。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PushMarketChartRange:
    """描述一个可用于推送图表展示和刷新的时间范围。"""

    value: str
    label: str
    short_label: str
    window_days: int


PUSH_MARKET_CHART_RANGES = {
    "3m": PushMarketChartRange("3m", "近3个月", "3M", 92),
    "6m": PushMarketChartRange("6m", "近6个月", "6M", 183),
    "1y": PushMarketChartRange("1y", "近1年", "1Y", 366),
    "2y": PushMarketChartRange("2y", "近2年", "2Y", 731),
    "3y": PushMarketChartRange("3y", "近3年", "3Y", 1096),
}
DEFAULT_PUSH_MARKET_CHART_RANGE = "1y"


def resolve_push_market_chart_range(value: object) -> PushMarketChartRange:
    """返回合法范围；非法值直接失败，避免推送区间静默漂移。"""
    normalized = str(value or DEFAULT_PUSH_MARKET_CHART_RANGE).strip().lower()
    try:
        return PUSH_MARKET_CHART_RANGES[normalized]
    except KeyError as error:
        raise ValueError(f"unsupported market_chart_range: {normalized}") from error
```

- [ ] **Step 4: Persist and expose the range in Push Center**

In `src/services/push_center_service.py`:

```python
from .push_market_chart_range import (
    DEFAULT_PUSH_MARKET_CHART_RANGE,
    resolve_push_market_chart_range,
)
```

Add to `DEFAULT_PUSH_CONFIG`:

```python
    "market_chart_range": DEFAULT_PUSH_MARKET_CHART_RANGE,
```

Add to `_normalize_config` after `report_style`:

```python
        merged["market_chart_range"] = resolve_push_market_chart_range(
            payload.get("market_chart_range", merged.get("market_chart_range"))
        ).value
```

Add `market_chart_range` to `_build_preview` and `_empty_preview` return dictionaries:

```python
            "market_chart_range": str(config.get("market_chart_range") or DEFAULT_PUSH_MARKET_CHART_RANGE),
```

Update `_resolve_requested_preview` so reuse also compares the range:

```python
        preview_range = resolve_push_market_chart_range(raw_preview.get("market_chart_range")).value
        config_range = resolve_push_market_chart_range(config.get("market_chart_range")).value
        if (
            preview_modules != config_modules
            or preview_style != config_style
            or preview_range != config_range
        ):
            return None
```

Return `market_chart_range` in the reusable preview:

```python
            "market_chart_range": preview_range,
```

Add `"market_chart_range": "1y"` after `"report_style": "newspaper"` in both tracked template JSON files.

- [ ] **Step 5: Run backend config tests and verify GREEN**

Run:

```powershell
uv run python -m pytest tests/test_push_center_api.py -k "market_chart_range or config_and_preview" -q
```

Expected: PASS.

- [ ] **Step 6: Commit the contract slice**

```powershell
git add src/services/push_market_chart_range.py src/services/push_center_service.py .data/push_center.json.template .data/push_center.template.json tests/test_push_center_api.py
git commit -m "feat: add push market chart range config"
```

## Task 2: Render Push Reports For The Selected Range

**Files:**
- Modify: `src/services/push_report_service.py:40-319`
- Modify: `src/services/push_report_service.py:329-570`
- Modify: `src/services/push_center_service.py:574-603`
- Test: `tests/test_push_workflow.py`
- Test: `tests/test_push_center_api.py`

- [ ] **Step 1: Write failing report range tests**

Add to `PushWorkflowTests`:

```python
    def test_report_service_renders_selected_market_chart_range(self):
        """校验报告按选择范围裁剪点位并同步更新所有范围文案。"""
        service = PushReportService()
        card = MarketCard(
            key="csi300",
            label="沪深300",
            close_value="3900",
            ma20_value="3850",
            signal="neutral",
            status="live",
            trade_date="2026-03-26",
            deviation_pct="+1.3%",
            source_label="akshare",
            explanation="说明",
            chart_points=[
                {"trade_date": "2024-03-20", "close_price": 3000.0, "ma20_price": 2990.0},
                {"trade_date": "2025-03-26", "close_price": 3500.0, "ma20_price": 3490.0},
                {"trade_date": "2026-03-26", "close_price": 3900.0, "ma20_price": 3850.0},
            ],
        )
        snapshot = DashboardSnapshot(
            generated_at="2026-03-26T08:00:00Z",
            news_mode="hybrid",
            title="日报",
            summary="概览",
            sections=[DashboardSection("market", "市场模型", "live", "desc")],
            dashboard_summary=SummaryBlock("日报", "概览", "2026-03-26", "", []),
            news_sections=[],
            macro_sections=[],
            market_sections=[card],
            event_sections=[],
            data_status=[DataStatusItem("market", "市场模型", "live", "ok")],
        )

        trend = service._build_market_trend_summary(card, market_chart_range="1y")
        markdown = service.build_markdown(snapshot, module_ids=["market"], market_chart_range="1y")
        html = service.build_email_html(snapshot, module_ids=["market"], market_chart_range="1y")

        self.assertEqual(trend["chart_points"][0]["trade_date"], "2025-03-26")
        self.assertIn("### 近1年趋势", markdown)
        self.assertIn("1Y Trend", html)
        self.assertIn("1Y 涨跌", html)
        self.assertIn("沪深300 近1年组合趋势图", html)
```

Update existing direct `_build_market_trend_summary(card)` calls to pass `market_chart_range="3m"` when preserving their current expectation.

- [ ] **Step 2: Run report test and verify RED**

Run:

```powershell
uv run python -m pytest tests/test_push_workflow.py -k "selected_market_chart_range" -q
```

Expected: FAIL because report methods still hard-code 3 months.

- [ ] **Step 3: Thread the range through report rendering**

In `src/services/push_report_service.py`, import:

```python
from .push_market_chart_range import (
    DEFAULT_PUSH_MARKET_CHART_RANGE,
    resolve_push_market_chart_range,
)
```

Add `market_chart_range: str = DEFAULT_PUSH_MARKET_CHART_RANGE` keyword arguments with these signatures:

```python
def build_markdown(
    self,
    snapshot: DashboardSnapshot,
    language: str = "en",
    *,
    module_ids: Iterable[str] | None = None,
    market_chart_range: str = DEFAULT_PUSH_MARKET_CHART_RANGE,
) -> str:

def build_email_html(
    self,
    snapshot: DashboardSnapshot,
    *,
    module_ids: Iterable[str] | None = None,
    layout: str = "newspaper",
    market_chart_range: str = DEFAULT_PUSH_MARKET_CHART_RANGE,
) -> str:

def _build_newspaper_body(self, snapshot: DashboardSnapshot, selected: set[str], *, market_chart_range: str) -> str:
def _build_briefing_body(self, snapshot: DashboardSnapshot, selected: set[str], *, market_chart_range: str) -> str:
def _build_market_column(self, snapshot: DashboardSnapshot, *, market_chart_range: str) -> str:
def _build_market_trend_block(self, card, *, market_chart_range: str) -> str:
def _build_market_trend_summary(self, card, *, market_chart_range: str) -> dict[str, object]:
def _extract_recent_market_points(self, card, *, market_chart_range: str) -> list[dict]:
def _render_market_combo_chart(self, points: list[dict[str, object]], *, label: str, market_chart_range: str) -> str:
```

Resolve once per method that needs labels:

```python
        range_spec = resolve_push_market_chart_range(market_chart_range)
```

Replace hard-coded copy:

```python
f"### {range_spec.label}趋势"
f"{range_spec.short_label} Trend"
f"{range_spec.short_label} 涨跌"
f"{escape(label)} {range_spec.label}组合趋势图"
```

Replace the fixed threshold in `_extract_recent_market_points`:

```python
        range_spec = resolve_push_market_chart_range(market_chart_range)
        threshold = latest_date - timedelta(days=range_spec.window_days)
        filtered = [point for trade_date, point in dated_points if trade_date >= threshold]
        return filtered or [point for _, point in dated_points[-65:]]
```

In `src/services/push_center_service.py`, pass the config value into both report builders:

```python
            market_chart_range = str(config.get("market_chart_range") or DEFAULT_PUSH_MARKET_CHART_RANGE)
            text_body = self._report_service.build_markdown(
                snapshot,
                module_ids=selected_modules,
                market_chart_range=market_chart_range,
            )
            html_body = self._report_service.build_email_html(
                snapshot,
                module_ids=selected_modules,
                layout=str(config.get("report_style") or "newspaper"),
                market_chart_range=market_chart_range,
            )
```

Update test report stubs in `tests/test_push_center_api.py` to accept and ignore `market_chart_range`.

- [ ] **Step 4: Run report and Push API tests**

Run:

```powershell
uv run python -m pytest tests/test_push_workflow.py tests/test_push_center_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit report rendering**

```powershell
git add src/services/push_report_service.py src/services/push_center_service.py tests/test_push_workflow.py tests/test_push_center_api.py
git commit -m "feat: render push charts by selected range"
```

## Task 3: Preserve Full History And Fetch The Selected Window

**Files:**
- Modify: `src/services/market_history_store.py:58-159`
- Modify: `src/services/market_monitoring_service.py:45-280`
- Modify: `src/services/dashboard_service.py:347-467`
- Modify: `src/services/dashboard_service.py:747-769`
- Modify: `src/providers/contracts.py:76-91`
- Modify: `src/providers/live_data.py:500-590`
- Modify: `src/providers/live_data.py:2272-2310`
- Modify: `src/providers/sample_data.py:360-425`
- Test: `tests/test_market_data_module.py`

- [ ] **Step 1: Replace deletion-oriented tests with retention and propagation tests**

In `tests/test_market_data_module.py`, replace the recent-window replacement test with:

```python
    def test_market_history_store_keeps_existing_rows_when_upserting_selected_window(self) -> None:
        """校验刷新选中范围时只更新同日期点，不删除范围内外已有历史。"""
        store = MarketHistoryStore(self.db_path)
        store.upsert_symbol_history(
            symbol="CSI300",
            display_name="沪深300",
            currency="CNY",
            provider_key="unit-test",
            source_url="https://example.com",
            points=[
                MarketIndexHistoryPoint(date(2024, 1, 1), 3600.0),
                MarketIndexHistoryPoint(date(2026, 3, 20), 3900.0),
                MarketIndexHistoryPoint(date(2026, 3, 23), 3910.0),
            ],
            status="live",
            window_label="近3年",
            warning_message="",
        )

        store.upsert_symbol_history(
            symbol="CSI300",
            display_name="沪深300",
            currency="CNY",
            provider_key="unit-test",
            source_url="https://example.com",
            points=[MarketIndexHistoryPoint(date(2026, 3, 23), 3950.0)],
            status="live",
            window_label="近3个月",
            warning_message="",
        )

        points = store.load_points(symbol="CSI300", end_date=date(2026, 3, 31), window_days=1096)
        self.assertEqual(
            [(point.trade_date, point.close_price) for point in points],
            [
                (date(2024, 1, 1), 3600.0),
                (date(2026, 3, 20), 3900.0),
                (date(2026, 3, 23), 3950.0),
            ],
        )
```

Update `RecordingProvider` in the refresh test:

```python
        class RecordingProvider:
            """记录窗口并返回完整历史帧。"""

            provider_key = "unit-test"

            def __init__(self):
                self.requested_windows = []

            def healthcheck(self) -> ProviderStatus:
                return ProviderStatus("unit-test", ProviderAvailability.LIVE, "", "2026-05-29T08:00:00Z")

            def fetch_index_snapshots(self, *, symbols, trade_date, history_window_days=180):
                self.requested_windows.append(history_window_days)
                points = tuple(
                    MarketIndexHistoryPoint(date(2026, 1, 1) + pd.Timedelta(days=offset), 4000.0 + offset)
                    for offset in range(149)
                )
                return [
                    MarketIndexSnapshot(
                        provider="unit-test",
                        symbol=symbols[0],
                        display_name="沪深300",
                        trade_date=trade_date,
                        close_price=4148.0,
                        currency="CNY",
                        source_url="https://example.com",
                        history_points=points,
                    )
                ]
```

Assert:

```python
        provider = RecordingProvider()
        store.upsert_symbol_history(
            symbol="CSI300",
            display_name="沪深300",
            currency="CNY",
            provider_key="unit-test",
            source_url="https://example.com",
            points=[MarketIndexHistoryPoint(date(2025, 12, 15), 9999.0)],
            status="live",
            window_label="近6个月",
            warning_message="",
        )
        service = MarketMonitoringService(
            market_provider=provider,
            store=store,
            registry={"CSI300": TrackedIndexDefinition("CSI300", "沪深300", "unit-test", "CNY")},
        )
        service.refresh_store(
            symbols=["CSI300"],
            trade_date=date(2026, 5, 29),
            history_window_days=731,
            progress_callback=progress_events.append,
        )
        self.assertEqual(provider.requested_windows, [731])
        self.assertIn(9999.0, [point.close_price for point in points])
```

Update the short-history test assertions to:

```python
        points = store.load_points(symbol="CSI300", end_date=date(2026, 5, 29), window_days=180)
        self.assertEqual(
            [(point.trade_date, point.close_price) for point in points],
            [
                (date(2026, 3, 15), 3999.0),
                (date(2026, 5, 25), 4100.0),
                (date(2026, 5, 26), 4101.0),
                (date(2026, 5, 27), 4102.0),
                (date(2026, 5, 28), 4103.0),
                (date(2026, 5, 29), 4104.0),
            ],
        )
        self.assertEqual(progress_events[-1]["status"], "completed")
```

- [ ] **Step 2: Run market tests and verify RED**

Run:

```powershell
uv run python -m pytest tests/test_market_data_module.py -k "market_history_store_keeps or market_refresh" -q
```

Expected: FAIL because store deletion, fixed provider windows, and short-sequence rejection still exist.

- [ ] **Step 3: Remove product deletion behavior**

In `src/services/market_history_store.py`, remove the `replace_from` argument, its docstring entry, and:

```python
            if replace_from is not None:
                connection.execute(
                    """
                    DELETE FROM market_index_daily
                    WHERE symbol = ?
                      AND trade_date >= ?
                    """,
                    (symbol, replace_from.isoformat()),
                )
```

In `src/services/market_monitoring_service.py`:

- Replace `replace_recent_window` with `history_window_days: int | None = None`.
- Resolve `effective_window_days = history_window_days or self._history_window_days`.
- Pass `effective_window_days` to `refresh_store`, `load_points`, provider calls, and `_resolve_history_window`.
- Remove `_can_replace_recent_window`.
- Remove the short-sequence rejection block.
- Remove the `replace_from` keyword argument from the store `upsert_symbol_history` call.

At the start of `build_snapshot` and `refresh_store`, normalize the optional request window:

```python
        effective_window_days = history_window_days or self._history_window_days
```

Use `effective_window_days` for provider calls, store reads, and coverage labels.

Replace `_resolve_history_window` with:

```python
    def _resolve_history_window(
        self,
        points: Sequence[MarketIndexHistoryPoint],
        *,
        target_window_days: int,
    ) -> tuple[str, str]:
        """根据请求窗口汇报覆盖程度，不删除已存在历史。"""
        if not points:
            return "", "未拉取到可用历史序列。"
        target_label = {
            92: "近3个月",
            183: "近6个月",
            366: "近1年",
            731: "近2年",
            1096: "近3年",
        }.get(target_window_days, f"近{target_window_days}天")
        coverage_days = (points[-1].trade_date - points[0].trade_date).days
        if coverage_days >= target_window_days - 15:
            return target_label, ""
        return f"近{coverage_days + 1}天", f"历史窗口未完整覆盖目标 {target_label}。"
```

The provider call becomes:

```python
                snapshots = self._market_provider.fetch_index_snapshots(
                    symbols=[symbol],
                    trade_date=trade_date,
                    history_window_days=effective_window_days,
                )
```

- [ ] **Step 4: Thread history window through Dashboard Service**

In `src/services/dashboard_service.py`, change market cache keys:

```python
    def build_market_module(
        self,
        *,
        force_refresh: bool = False,
        history_window_days: int | None = None,
    ) -> tuple[str, List[MarketCard]]:
        """Build one frontend-ready market module."""
        cache_key = f"module:market:{history_window_days or 'default'}"
        return self._get_or_build_module(
            cache_key,
            lambda: self._build_market_module_uncached(
                force_refresh=force_refresh,
                history_window_days=history_window_days,
            ),
            force_refresh=force_refresh,
        )
```

Change `rebuild_market_module`, `_build_market_module_uncached`, and `_build_market_service_snapshot` to accept and forward `history_window_days`. Keep the TypeError compatibility fallback, but replace `"replace_recent_window"` with `"history_window_days"`.

- [ ] **Step 5: Thread history window through provider contracts**

In `src/providers/contracts.py`:

```python
    def fetch_index_snapshots(
        self,
        *,
        symbols: Sequence[str],
        trade_date: date,
        history_window_days: int = 180,
    ) -> Sequence[MarketIndexSnapshot]:
        """Return normalized broad-index snapshots for the requested history window."""
```

In `AkshareMarketDataProvider`, add `history_window_days: int = 180` to `fetch_index_snapshots` and `_load_market_frame`, and replace both fixed `timedelta(days=180)` expressions with `timedelta(days=history_window_days)`.

In `FallbackMarketDataProvider`, accept and forward `history_window_days` to primary and fallback calls.

In `SampleMarketDataProvider`, accept `history_window_days: int = 180`, pass it into `_build_history_points`, and generate sample points from:

```python
        cursor = trade_date - timedelta(days=history_window_days + 30)
```

- [ ] **Step 6: Run market regression and verify GREEN**

Run:

```powershell
uv run python -m pytest tests/test_market_data_module.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit retained-history refresh**

```powershell
git add src/services/market_history_store.py src/services/market_monitoring_service.py src/services/dashboard_service.py src/providers/contracts.py src/providers/live_data.py src/providers/sample_data.py tests/test_market_data_module.py
git commit -m "feat: retain push market history across range refreshes"
```

## Task 4: Add Lightweight Preview Redraw And Range-Aware Full Refresh

**Files:**
- Modify: `src/services/push_center_service.py:217-292`
- Modify: `src/services/push_center_service.py:386-413`
- Modify: `src/services/push_center_service.py:622-705`
- Modify: `src/app/web/fastapi_app.py:339-369`
- Test: `tests/test_push_center_api.py`

- [ ] **Step 1: Write failing Push API orchestration tests**

Extend `ModuleOnlyDashboardService`:

```python
    def __init__(self):
        self.build_snapshot_calls = []
        self.build_market_module_calls = []

    def build_market_module(self, *, force_refresh=False, history_window_days=None):
        self.build_market_module_calls.append((force_refresh, history_window_days))
        return (
            "2026-03-24T08:00:00Z",
            [
                MarketCard(
                    key="csi300",
                    label="沪深300",
                    close_value="3900",
                    ma20_value="3850",
                    signal="neutral",
                    status="live",
                    trade_date="2026-03-24",
                    deviation_pct="+1.3%",
                    source_label="akshare",
                    explanation="说明",
                    chart_points=[],
                )
            ],
        )
```

Extend `ChartRefreshDashboardService`:

```python
    def __init__(self):
        super().__init__()
        self.rebuild_market_module_calls = []

    def rebuild_market_module(self, *, history_window_days=None, progress_callback=None):
        self.rebuild_market_module_calls.append(history_window_days)
        if progress_callback is not None:
            progress_callback(
                {
                    "symbol": "CSI300",
                    "label": "沪深300",
                    "status": "completed",
                    "completed": 1,
                    "total": 1,
                    "message": "沪深300 刷新完成。",
                }
            )
        return self.build_market_module(
            force_refresh=True,
            history_window_days=history_window_days,
        )
```

Add:

```python
    def test_preview_can_redraw_selected_range_without_external_refresh(self):
        """校验范围切换仅使用本地历史重绘，不触发外部市场刷新。"""
        dashboard_service = ModuleOnlyDashboardService()
        push_service = PushCenterService(
            dashboard_service=dashboard_service,
            report_service=StubPushReportService(),
            config_path=self.temp_dir / "range-redraw.json",
            enable_scheduler=False,
        )
        try:
            result = push_service.build_preview_response(
                {"config": {"market_chart_range": "2y"}, "refresh_data": False}
            )
            self.assertTrue(result["preview"]["ok"])
            self.assertEqual(dashboard_service.build_market_module_calls, [(False, 731)])
        finally:
            push_service.stop_scheduler()

    def test_market_chart_refresh_uses_selected_range(self):
        """校验全量刷新按当前草稿范围获取历史。"""
        dashboard_service = ChartRefreshDashboardService()
        push_service = PushCenterService(
            dashboard_service=dashboard_service,
            report_service=StubPushReportService(),
            config_path=self.temp_dir / "range-refresh.json",
            enable_scheduler=False,
        )
        try:
            response = push_service.start_market_chart_refresh(
                {"config": {"market_chart_range": "3y"}}
            )
            job_id = response["job"]["id"]
            for _ in range(30):
                job = push_service.get_market_chart_refresh(job_id)["job"]
                if job["status"] == "completed":
                    break
                time.sleep(0.01)
            self.assertEqual(dashboard_service.rebuild_market_module_calls, [1096])
            self.assertIn("近3年", job["message"])
        finally:
            push_service.stop_scheduler()
```

- [ ] **Step 2: Run Push API orchestration tests and verify RED**

Run:

```powershell
uv run python -m pytest tests/test_push_center_api.py -k "redraw_selected_range or refresh_uses_selected_range" -q
```

Expected: FAIL because range and `refresh_data` are not threaded through orchestration.

- [ ] **Step 3: Add preview redraw mode**

In `PushCenterService.build_preview_response`:

```python
    def build_preview_response(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        request_payload = payload
        payload = self._unwrap_payload(payload)
        existing = self._load_config()
        normalized = self._normalize_config(payload or {}, base=existing)
        refresh_data = True
        if isinstance(request_payload, Mapping) and "refresh_data" in request_payload:
            refresh_data = bool(request_payload.get("refresh_data"))
        return {
            "generated_at": _utc_now_iso(),
            "config": self._public_config(normalized),
            "preview": self._build_preview(normalized, force_refresh=refresh_data),
        }
```

- [ ] **Step 4: Thread selected range through module construction and full refresh**

In `_build_push_snapshot`, resolve config range before calling market module. Change its signature to accept `market_chart_range`, and call:

```python
                range_spec = resolve_push_market_chart_range(market_chart_range)
                _, market_sections = self._dashboard_service.build_market_module(
                    force_refresh=force_refresh,
                    history_window_days=range_spec.window_days,
                )
```

In `_build_preview`, pass config range to `_build_push_snapshot`.

In `_run_market_chart_refresh`:

```python
            range_spec = resolve_push_market_chart_range(config.get("market_chart_range"))
            if callable(rebuild_market_module):
                rebuild_market_module(
                    history_window_days=range_spec.window_days,
                    progress_callback=lambda event: self._update_market_chart_refresh_progress(job_id, event),
                )
```

Replace the successful completion message with:

```python
                    job["message"] = f"{range_spec.label}宽基指数历史已刷新，预览图已重绘。"
```

Update `src/app/web/fastapi_app.py` docstrings to describe selected-range refresh rather than fixed three-month replacement.

- [ ] **Step 5: Run Push API regression and verify GREEN**

Run:

```powershell
uv run python -m pytest tests/test_push_center_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Push orchestration**

```powershell
git add src/services/push_center_service.py src/app/web/fastapi_app.py tests/test_push_center_api.py
git commit -m "feat: redraw and refresh push charts by draft range"
```

## Task 5: Add Frontend Range Types And Request Semantics

**Files:**
- Modify: `frontend/src/features/push/model/push-module.types.ts`
- Modify: `frontend/src/features/push/model/push-module-adapter.ts`
- Modify: `frontend/src/features/push/api/preview-push.ts`
- Modify: `frontend/src/app/__tests__/workbench-api-mocks.ts`
- Create: `frontend/src/features/push/__tests__/push-module-adapter.test.ts`
- Create: `frontend/src/features/push/__tests__/push-api.test.ts`

- [ ] **Step 1: Write failing frontend adapter and request tests**

Create `frontend/src/features/push/__tests__/push-module-adapter.test.ts`:

```tsx
import { describe, expect, it } from "vitest";
import { adaptPushConfig, toPushConfigRaw } from "../model/push-module-adapter";
import type { PushConfigRaw } from "../model/push-module.types";

const legacyConfig: PushConfigRaw = {
  selected_module_ids: ["market"],
  report_style: "newspaper",
  email: {
    enabled: true,
    label: "Primary Email",
    smtp_server: "smtp.example.com",
    smtp_port: 587,
    use_tls: true,
    username: "",
    password: "",
    from_address: "",
    to_addresses: "",
  },
  schedules: [],
};

describe("push module adapter", () => {
  it("defaults old push config payloads to one year", () => {
    expect(adaptPushConfig(legacyConfig).marketChartRange).toBe("1y");
  });

  it("serializes the selected push chart range", () => {
    const config = { ...adaptPushConfig(legacyConfig), marketChartRange: "2y" as const };
    expect(toPushConfigRaw(config).market_chart_range).toBe("2y");
  });
});
```

Create `frontend/src/features/push/__tests__/push-api.test.ts`:

```tsx
import { afterEach, describe, expect, it, vi } from "vitest";
import { previewPush } from "../api/preview-push";
import { adaptPushConfig } from "../model/push-module-adapter";
import type { PushConfigRaw } from "../model/push-module.types";

const rawConfig = {
  selected_module_ids: ["market"],
  report_style: "newspaper",
  market_chart_range: "2y",
  email: {
    enabled: true,
    label: "Primary Email",
    smtp_server: "smtp.example.com",
    smtp_port: 587,
    use_tls: true,
    username: "",
    password: "",
    from_address: "",
    to_addresses: "",
  },
  schedules: [],
} satisfies PushConfigRaw;

describe("previewPush", () => {
  afterEach(() => vi.restoreAllMocks());

  it("requests a local redraw without refreshing external data", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        generated_at: "2026-06-01T00:00:00Z",
        config: rawConfig,
        preview: {
          ok: true,
          generated_at: "2026-06-01T00:00:00Z",
          subject: "Market Daily",
          text_body: "",
          html_body: "<p>preview</p>",
          style: "newspaper",
          market_chart_range: "2y",
          selected_module_ids: ["market"],
        },
      }), { status: 200, headers: { "Content-Type": "application/json" } }),
    );

    await previewPush(adaptPushConfig(rawConfig), { refreshData: false });

    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toMatchObject({
      config: { market_chart_range: "2y" },
      refresh_data: false,
    });
  });
});
```

- [ ] **Step 2: Run frontend request tests and verify RED**

Run:

```powershell
cmd /c npm run test -- src/features/push/__tests__/push-module-adapter.test.ts src/features/push/__tests__/push-api.test.ts --run
```

Expected: FAIL because the range types, adapter fields, and `refreshData` request option do not exist.

- [ ] **Step 3: Add frontend range types and adapters**

In `push-module.types.ts`:

```ts
export type PushMarketChartRange = "3m" | "6m" | "1y" | "2y" | "3y";

export const PUSH_MARKET_CHART_RANGE_OPTIONS: ReadonlyArray<{
  value: PushMarketChartRange;
  label: string;
}> = [
  { value: "3m", label: "3个月" },
  { value: "6m", label: "6个月" },
  { value: "1y", label: "1年" },
  { value: "2y", label: "2年" },
  { value: "3y", label: "3年" },
];
```

Add optional raw fields for backward compatibility:

```ts
market_chart_range?: PushMarketChartRange;
```

to `PushConfigRaw` and `PushPreviewRaw`, and:

```ts
marketChartRange: PushMarketChartRange;
```

to `PushConfig` and `PushPreview`.

In `push-module-adapter.ts`, add `marketChartRange: "1y"` to `DEFAULT_CONFIG`, adapt missing raw values with `?? "1y"`, and serialize back to `market_chart_range`.

- [ ] **Step 4: Add lightweight preview request option**

Replace `previewPush` with:

```ts
export async function previewPush(
  config: PushConfig,
  options: { refreshData?: boolean } = {},
): Promise<PushPreviewResponseRaw> {
  const response = await fetch("/api/push/preview", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      config: toPushConfigRaw(config),
      refresh_data: options.refreshData ?? true,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `push preview failed: ${response.status}`);
  }
  return payload as PushPreviewResponseRaw;
}
```

Add this Chinese function comment immediately above `previewPush`:

```ts
/** 按当前草稿重绘预览；可选择是否先刷新外部数据。 */
```

Update `workbench-api-mocks.ts` Push config and preview fixtures to include `market_chart_range: "1y"`.

- [ ] **Step 5: Run frontend request tests**

Run:

```powershell
cmd /c npm run test -- src/features/push/__tests__/push-module-adapter.test.ts src/features/push/__tests__/push-api.test.ts --run
```

Expected: PASS.

- [ ] **Step 6: Commit frontend contract**

```powershell
git add frontend/src/features/push/model/push-module.types.ts frontend/src/features/push/model/push-module-adapter.ts frontend/src/features/push/api/preview-push.ts frontend/src/app/__tests__/workbench-api-mocks.ts frontend/src/features/push/__tests__/push-module-adapter.test.ts frontend/src/features/push/__tests__/push-api.test.ts
git commit -m "feat: add push chart range frontend contract"
```

## Task 6: Build Full-Width Preview Toolbar And Settings Dialog

**Files:**
- Create: `frontend/src/features/push/components/push-flash-message.tsx`
- Create: `frontend/src/features/push/components/push-settings-dialog.tsx`
- Modify: `frontend/src/features/push/components/push-config-form.tsx`
- Modify: `frontend/src/features/push/components/push-preview-panel.tsx`
- Modify: `frontend/src/pages/push-page.tsx`
- Modify: `frontend/src/features/push/__tests__/push-page.test.tsx`
- Modify: `frontend/src/features/push/__tests__/push-preview-panel.test.tsx`

- [ ] **Step 1: Write failing layout and accessibility tests**

Update `push-page.test.tsx` first-page test:

```tsx
    expect(await screen.findByTitle("Push preview")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Delivery configuration" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Schedule editor" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "打开推送设置" }));

    expect(screen.getByRole("dialog", { name: "推送设置" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Delivery configuration" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Schedule editor" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save configuration" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Refresh preview" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send now" })).not.toBeInTheDocument();
```

In `push-preview-panel.test.tsx`, add:

```tsx
  it("renders compact accessible preview actions", () => {
    render(
      <PushPreviewPanel
        marketChartRange="1y"
        onMarketChartRangeChange={() => undefined}
        onOpenSettings={() => undefined}
        onPreview={() => undefined}
        onRefreshCharts={() => undefined}
        onSend={() => undefined}
        preview={buildPreview()}
        refreshAfterMs={30000}
      />,
    );

    expect(screen.getByLabelText("宽基指数时间范围")).toHaveValue("1y");
    for (const label of ["打开推送设置", "全量刷新图表", "刷新预览", "立即发送"]) {
      expect(screen.getByRole("button", { name: label })).toHaveAttribute("title", label);
    }
  });
```

Extract the repeated preview fixture in this test file into a local `buildPreview()` helper including `marketChartRange: "1y"`.

In `push-page.test.tsx`, add:

```tsx
  it("redraws the preview locally when the market chart range changes", async () => {
    const fetchMock = installWorkbenchFetchMock({ push: pushPayload, market: marketPayload });
    const user = userEvent.setup();
    renderPushApp("/push?tab=schedules");

    await user.selectOptions(await screen.findByLabelText("宽基指数时间范围"), "2y");

    await waitFor(() => {
      const previewCall = fetchMock.mock.calls.find(
        ([input, init]) => String(input).includes("/api/push/preview") && init?.method === "POST",
      );
      expect(JSON.parse(String(previewCall?.[1]?.body))).toMatchObject({
        config: { market_chart_range: "2y" },
        refresh_data: false,
      });
    });
  });
```

Update the existing full-refresh and manual-send page tests to parse the POST body and assert:

```tsx
expect(JSON.parse(String(requestCall?.[1]?.body))).toMatchObject({
  config: { market_chart_range: "1y" },
});
```

- [ ] **Step 2: Run frontend component tests and verify RED**

Run:

```powershell
cmd /c npm run test -- src/features/push/__tests__/push-preview-panel.test.tsx src/features/push/__tests__/push-page.test.tsx --run
```

Expected: FAIL because the modal, select, and icon-only toolbar do not exist.

- [ ] **Step 3: Extract reusable flash message**

Create `push-flash-message.tsx`:

```tsx
type PushFlashMessageProps = {
  flash: { tone: "success" | "error" | "neutral"; message: string } | null;
};

/** 展示 Push Center 操作结果，供预览页和设置弹窗复用。 */
export function PushFlashMessage({ flash }: PushFlashMessageProps) {
  if (!flash) {
    return null;
  }
  return (
    <div
      className={[
        "rounded-2xl border px-4 py-3 text-sm",
        flash.tone === "success"
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : flash.tone === "error"
            ? "border-rose-200 bg-rose-50 text-rose-700"
            : "border-slate-200 bg-slate-50 text-slate-700",
      ].join(" ")}
    >
      {flash.message}
    </div>
  );
}
```

- [ ] **Step 4: Shrink config form to edit and save only**

In `push-config-form.tsx`:

- Remove `flash`, `isPreviewing`, `isSending`, `onPreview`, and `onSend`.
- Set `const busy = isSaving`.
- Remove the inline flash block.
- Keep only the save button.
- Update the description to:

```tsx
Tune the active modules, report style, and SMTP delivery profile before saving.
```

- [ ] **Step 5: Create the settings dialog**

Create `push-settings-dialog.tsx`:

```tsx
import { XMarkIcon } from "@heroicons/react/24/outline";
import type {
  PushChannelOption,
  PushConfig,
  PushSourceModuleOption,
  PushStyleOption,
} from "../model/push-module.types";
import { PushConfigForm } from "./push-config-form";
import { PushFlashMessage } from "./push-flash-message";
import { PushSchedulesEditor } from "./push-schedules-editor";

type PushSettingsDialogProps = {
  draft: PushConfig;
  channelTypeOptions: PushChannelOption[];
  sourceModuleOptions: PushSourceModuleOption[];
  styleOptions: PushStyleOption[];
  flash: { tone: "success" | "error" | "neutral"; message: string } | null;
  isSaving: boolean;
  onClose: () => void;
  onDraftChange: (next: PushConfig) => void;
  onSave: () => void;
};

/** 收纳 Push Center 计划任务和投递配置，关闭时保留页面草稿。 */
export function PushSettingsDialog(props: PushSettingsDialogProps) {
  return (
    <div
      aria-labelledby="push-settings-title"
      aria-modal="true"
      className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/40 p-4"
      role="dialog"
    >
      <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-3xl bg-slate-50 p-5 shadow-xl sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Configuration</p>
            <h3 className="mt-2 text-xl font-semibold text-slate-950" id="push-settings-title">推送设置</h3>
          </div>
          <button aria-label="关闭推送设置" className="rounded-full border border-slate-200 bg-white p-2 text-slate-600" onClick={props.onClose} type="button">
            <XMarkIcon aria-hidden="true" className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-5"><PushFlashMessage flash={props.flash} /></div>
        <div className="mt-5 space-y-6">
          <PushSchedulesEditor
            channelTypeOptions={props.channelTypeOptions}
            onSchedulesChange={(schedules) => props.onDraftChange({ ...props.draft, schedules })}
            schedules={props.draft.schedules}
            sourceModuleOptions={props.sourceModuleOptions}
          />
          <PushConfigForm
            channelTypeOptions={props.channelTypeOptions}
            draft={props.draft}
            isSaving={props.isSaving}
            onDraftChange={props.onDraftChange}
            onSave={props.onSave}
            sourceModuleOptions={props.sourceModuleOptions}
            styleOptions={props.styleOptions}
          />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Build the icon-only preview toolbar**

In `push-preview-panel.tsx`, import:

```tsx
import {
  ArrowPathIcon,
  ArrowPathRoundedSquareIcon,
  Cog6ToothIcon,
  PaperAirplaneIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { PUSH_MARKET_CHART_RANGE_OPTIONS, type PushMarketChartRange, type PushMarketChartRefreshJob, type PushPreview } from "../model/push-module.types";
import { PushFlashMessage } from "./push-flash-message";
```

Add props for `flash`, `marketChartRange`, `onMarketChartRangeChange`, `onOpenSettings`, `onPreview`, `onSend`, `isPreviewing`, and `isSending`.

Replace the toolbar with a wrapping control group:

```tsx
        <div className="flex max-w-md flex-wrap items-center justify-end gap-2">
          <label className="text-xs font-medium text-slate-700">
            <span className="sr-only">宽基指数时间范围</span>
            <select
              aria-label="宽基指数时间范围"
              className="rounded-full border border-slate-300 bg-white px-3 py-2"
              onChange={(event) => onMarketChartRangeChange?.(event.target.value as PushMarketChartRange)}
              value={marketChartRange}
            >
              {PUSH_MARKET_CHART_RANGE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <IconAction label="打开推送设置" onClick={onOpenSettings} icon={<Cog6ToothIcon aria-hidden="true" className="h-4 w-4" />} />
          <IconAction disabled={isChartRefreshing} label="全量刷新图表" onClick={onRefreshCharts} icon={<ArrowPathIcon aria-hidden="true" className={isChartRefreshing ? "h-4 w-4 animate-spin" : "h-4 w-4"} />} />
          <IconAction disabled={isPreviewing} label="刷新预览" onClick={onPreview} icon={<ArrowPathRoundedSquareIcon aria-hidden="true" className="h-4 w-4" />} />
          <IconAction disabled={isSending} label="立即发送" onClick={onSend} icon={<PaperAirplaneIcon aria-hidden="true" className="h-4 w-4" />} />
        </div>
```

Add:

```tsx
function IconAction({
  disabled = false,
  icon,
  label,
  onClick,
}: {
  disabled?: boolean;
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
}) {
  if (!onClick) {
    return null;
  }
  return (
    <button
      aria-label={label}
      className="rounded-full border border-slate-300 bg-white p-2 text-slate-700 transition hover:border-slate-400 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
      disabled={disabled}
      onClick={onClick}
      title={label}
      type="button"
    >
      {icon}
    </button>
  );
}
```

Add this Chinese function comment immediately above `IconAction`:

```tsx
/** 渲染带悬停提示和键盘焦点状态的紧凑图标按钮。 */
```

Render `<PushFlashMessage flash={flash} />` below the header.

- [ ] **Step 7: Make Schedules a full-width preview page**

In `push-page.tsx`:

- Add `const [isSettingsOpen, setIsSettingsOpen] = useState(false);`.
- Change preview mutation input to `{ config, refreshData }`.
- For the explicit refresh icon, call `previewMutation.mutate({ config: draft, refreshData: true })`.
- For range changes, construct `nextDraft`, call `setDraft(nextDraft)`, then `previewMutation.mutate({ config: nextDraft, refreshData: false })`.
- Render `PushPreviewPanel` as `main` for `schedules`.
- Pass `side={null}` and `contentLayoutClassName="grid gap-6"` for both tabs.
- Render `PushSettingsDialog` after `ModulePageFrame` only when `activeTab === "schedules" && isSettingsOpen`.
- Pass `onOpenSettings={() => setIsSettingsOpen(true)}` into `PushPreviewPanel`.
- Keep `History` behavior unchanged.

- [ ] **Step 8: Run frontend Push tests and verify GREEN**

Run:

```powershell
cmd /c npm run test -- src/features/push/__tests__/push-preview-panel.test.tsx src/features/push/__tests__/push-page.test.tsx --run
```

Expected: PASS.

- [ ] **Step 9: Run frontend build**

Run:

```powershell
cmd /c npm run build
```

Expected: PASS. The existing Vite chunk-size warning may remain.

- [ ] **Step 10: Commit UI redesign**

```powershell
git add frontend/src/features/push/components/push-flash-message.tsx frontend/src/features/push/components/push-settings-dialog.tsx frontend/src/features/push/components/push-config-form.tsx frontend/src/features/push/components/push-preview-panel.tsx frontend/src/pages/push-page.tsx frontend/src/features/push/__tests__/push-page.test.tsx frontend/src/features/push/__tests__/push-preview-panel.test.tsx
git commit -m "feat: move push settings into preview dialog"
```

## Task 7: Update Documentation And Run Full Verification

**Files:**
- Modify: `README.md:169-181`
- Modify: `CHANGELOG.md`
- Modify: `docs/api-contract.md:360-435`
- Modify: `docs/test-strategy.md`
- Review: `.data/*.db`

- [ ] **Step 1: Update user-facing documentation**

Add a top-level CHANGELOG entry describing:

```markdown
- Push Center `Schedules` 页面改为全宽日报预览，计划任务和投递配置收纳到齿轮设置弹窗；预览页新增图标化刷新、发送操作和宽基指数时间范围下拉框。
- 宽基指数图表支持 `3个月 / 6个月 / 1年 / 2年 / 3年`，默认近 `1年`；全量刷新按当前范围抓取并仅按日期 `upsert`，保留 SQLite 中既有历史。
```

Update `docs/api-contract.md`:

- Add `market_chart_range` to Push config request examples.
- Document allowed values and `1y` default.
- Document `POST /api/push/preview` request option `refresh_data`.
- Replace fixed-three-month replacement language in `POST /api/push/market-chart-refresh`.

Update `README.md` Push Center section with default one-year push charts, selectable ranges, and retained SQLite history.

Update `docs/test-strategy.md` Push regression checklist with range persistence, local redraw, range-aware full refresh, and history retention.

- [ ] **Step 2: Run diff hygiene checks**

Run:

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors. Preserve unrelated pre-existing worktree changes.

- [ ] **Step 3: Run backend regression**

Run:

```powershell
uv run python -m pytest -q
```

Expected: all backend tests pass. Existing FastAPI `on_event` deprecation warnings may remain.

- [ ] **Step 4: Run frontend regression and build**

Run:

```powershell
cmd /c npm run test -- --run
cmd /c npm run build
```

Working directory: `frontend/`

Expected: all Vitest tests pass and Vite build succeeds. Existing chunk-size warning may remain.

- [ ] **Step 5: Perform local browser QA**

Start the local app using the repository’s existing development command, then use the Browser plugin to verify:

1. `/push?tab=schedules` shows one full-width preview card.
2. The range dropdown defaults to `1年`.
3. The four icon buttons expose hover titles.
4. The gear button opens the scrollable settings dialog.
5. Closing and reopening the dialog keeps unsaved edits.
6. Switching to `2年` redraws preview without starting a full-refresh progress dialog.
7. Clicking full refresh opens the progress dialog.
8. `History` still hides the preview and settings controls.

- [ ] **Step 6: Review database changes before staging**

Run:

```powershell
git status --short .data
```

Rules:

- Keep any intentional `.data/*.db` history updates and include them in the final commit, per project policy.
- Do not stage database changes created only by tests or changes that existed before this implementation.
- Do not modify or stage `.third_part_newsnow/`.

- [ ] **Step 7: Commit docs and intentional data updates**

```powershell
git add README.md CHANGELOG.md docs/api-contract.md docs/test-strategy.md
git add .data/*.db
git commit -m "docs: document push chart range controls"
```

Only run `git add .data/*.db` when Step 6 identifies intentional history updates. Otherwise omit that command.

## Final Regression Checklist

1. 原功能验证点：配置保存、预览刷新、立即发送、定时发送、执行历史和异步刷新进度正常。
2. 新功能验证点：全宽预览、齿轮弹窗、五档范围、默认近一年、本地轻量重绘、按范围全量刷新正常。
3. 边界情况：旧配置缺字段自动补 `1y`；非法范围返回 `400`；短序列只追加可用点；范围外旧数据保留。
4. 异常处理：单指数失败不阻断其他指数；预览失败和发送失败展示提示；草稿关闭弹窗后仍保留。
5. 配置兼容性：现有 JSON 无需人工迁移；接口 snake_case 与前端 camelCase adapter 同步；历史 SQLite 不做删除。
