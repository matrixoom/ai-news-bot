# 接口契约（API Contract）

本文档描述当前仍对前端开放的 HTTP 接口。Dashboard、News、Market、Events 页面与聚合 API 已按需求移除；Macro Data 与 Push Center 相关后端逻辑保留。

## 1. 约定总览

- Base URL：`http://127.0.0.1:8000`
- 返回格式：JSON（除页面入口与错误 HTML）
- 模块加载中语义：
  - HTTP `202`
  - `module.loading = true`
  - `refresh_after_ms` 提示前端重试间隔

## 2. 页面与健康接口

| 路径 | 方法 | 说明 |
| --- | --- | --- |
| `/` | GET | SPA 可用时重定向到 `/push`；否则返回 workbench unavailable |
| `/macro-data` | GET | Macro Data SPA 入口 |
| `/event-outlook` | GET | Outlook SPA 入口，国内/国际时间轴 |
| `/notes` | GET | Notes SPA 入口，当前为空目录页 |
| `/market-data` | GET | Market Data SPA 入口 |
| `/push` | GET | Push Center SPA 入口 |
| `/settings` | GET | Settings SPA 入口 |
| `/healthz` | GET | 健康检查，返回 `{"status":"ok"}` |

已移除：`/dashboard`、`/news`、`/macro`、`/market`、`/events`、`/status`、`/legacy`。

## 3. 已移除的聚合与模块接口

以下接口不再对前端提供服务，预期返回 `404`：

- `GET /api/dashboard`
- `GET /api/frontend/dashboard`
- `GET /api/frontend/modules/news`
- `GET /api/frontend/modules/macro`
- `GET /api/frontend/modules/market`
- `GET /api/frontend/modules/events`
- `GET /api/frontend/modules/status`

说明：Push Center 日报生成仍会在后端内部复用必要的数据快照能力，但这些能力不再作为 Dashboard/News/Macro/Market/Events 页面 API 暴露。新增 Macro Data 使用 `/api/frontend/modules/macro-data` 独立契约，不复用已移除的 `/api/frontend/modules/macro`。

## 4. 保留模块接口

### 4.1 `GET /api/frontend/modules/macro-data`

查询参数：

- `tab`：`gdp | credit | climate | trade | prices | currency | expectations | employment`，默认 `gdp`

用途：返回 Macro Data 模块元数据、子标签、时间范围选项和当前分类下的图表定义。

兼容说明：景气标签包含 `manufacturing_pmi`、`non_manufacturing_pmi`、`comprehensive_pmi` 三个 PMI 折线图；信贷标签的 `new_rmb_loans` 与 `household_demand_deposits` 使用 `chart_type: "bar_stacked_line"`。`new_rmb_loans` 返回总量虚线折线，居民/企业短期与长期贷款各自返回同名堆叠柱与虚线折线；`household_demand_deposits` 返回居民存款总计虚线折线，以及居民活期存款、居民定期及其他存款同名堆叠柱与虚线折线。就业标签包含 `unemployment_insurance_fund_expense` 年度折线图，标题为 `中国社会保险基金支出:失业保险:累计值`，单位为亿元；默认种子覆盖 2005-2024 年 20 个年度点，状态为 `live`。前端图例选中/取消时同名柱线同步联动。

成功：`200`

```json
{
  "generated_at": "2026-05-01T00:00:00Z",
  "module": {
    "id": "macro-data",
    "label": "Macro Data",
    "description": "GDP, credit, leverage, and inflation indicators",
    "status": "live",
    "loading": false
  },
  "tab": "gdp",
  "default_range": "1y",
  "default_frequency": "quarterly",
  "frequency_options": [
    { "value": "quarterly", "label": "季度" },
    { "value": "yearly", "label": "年度" }
  ],
  "charts": [
    {
      "id": "nominal_gdp",
      "title": "名义GDP",
      "unit": "亿元",
      "frequency": "quarterly",
      "status": "sample"
    },
    {
      "id": "real_gdp",
      "title": "实际GDP",
      "unit": "亿元",
      "frequency": "quarterly",
      "status": "sample"
    },
    {
      "id": "gdp_growth",
      "title": "GDP增速",
      "unit": "%",
      "frequency": "quarterly",
      "status": "sample"
    }
  ]
}
```

失败：

- `400`：`invalid_macro_data_tab`
- `503`：`frontend_macro_data_module_unavailable`

### 4.2 `GET /api/frontend/modules/macro-data/charts/{chart_id}`

查询参数：

- `range`：`6m | 1y | 3y | 5y | 10y | 15y | 20y | 25y | 30y | custom`，默认 `1y`
- `start_date`：自定义范围起始日期，`YYYY-MM-DD`
- `end_date`：自定义范围结束日期，`YYYY-MM-DD`
- `frequency`：`monthly | quarterly | yearly`；未传入时按指标默认频率读取，例如月度指标继续使用 `monthly`

用途：按单张图表读取 SQLite 中对应指标表的数据。基础指标分别持久化在 `.data/macro_data.db` 的独立事实表中，例如 `macro_nominal_gdp`、`macro_cpi`。事实表以 `(period_end, frequency)` 作为幂等键，年度 `YYYY-12-31` 与四季度 `YYYYQ4` 可同时保存，不会互相覆盖。`gdp_growth` 为组合图表，优先读取本地持久化的 `macro_nominal_gdp_growth` 与 `macro_real_gdp_growth`，缺少增长表时再基于 `macro_nominal_gdp` 与 `macro_real_gdp` 回退计算同比增速。

同步命令：

```bash
uv run python main.py macro-sync
```

当前 GDP 同步策略：

- 名义 GDP：World Bank 年度人民币 GDP + 东方财富/AkShare 季度累计值。
- 名义 GDP：World Bank 年度人民币 GDP + 东方财富/AkShare 季度累计值；季度图展示当季值，年度图优先使用完整四季度合计，保证同年四个季度之和与年度值一致。
- 实际 GDP：World Bank 年度不变价人民币 GDP + 可访问的不变价 GDP 镜像近年季度当季值；年度图优先使用完整四季度合计。
- GDP 增速：从本地同频率总量点位同比推导，年度和季度分开计算。
- 景气 PMI：制造业 PMI、非制造业 PMI 与综合 PMI 分别写入独立事实表。
- 信贷细分：人民银行贷款余额表按列序修正 10 月列，避免 Excel `2025.1` 显示导致 10 月被误解析为 1 月；`new_rmb_loans` 图表返回总量虚线 + 四项细分堆叠柱和同名虚线折线。
- 居民存款：`household_demand_deposits` 图表读取 `macro_household_deposits`、`macro_household_demand_deposits`、`macro_household_time_deposits` 三张事实表；同步优先解析人民银行 2000 年以来归档 HTML 与 2015 年以来年度 Excel，覆盖近 30 年窗口中的月度余额。
- 就业：`unemployment_insurance_fund_expense` 图表读取 `macro_unemployment_insurance_fund_expense` 年度事实表；2005-2010 年点位来自国家统计局《中国统计年鉴 2011》21-37 表，2011-2023 年点位来自《中国统计年鉴 2024》24-24 表，2024 年点位采用人社部《2024年度人力资源和社会保障事业发展统计公报》的 `1842` 亿元。财政部《2024年全国社会保险基金支出决算表》披露同项决算数为 `1842.21` 亿元，仅作为精度更高的交叉校验来源。

成功：`200`

```json
{
  "id": "nominal_gdp",
  "title": "名义GDP",
  "unit": "亿元",
  "frequency": "quarterly",
  "range": {
    "type": "1y",
    "start_date": "2025-05-01",
    "end_date": "2026-05-01"
  },
  "series": [
    {
      "name": "名义GDP",
      "points": [
        { "date": "2026-03-31", "period_label": "2026Q1", "value": 322000, "unit": "亿元" }
      ]
    }
  ]
}
```

`gdp_growth` 成功响应示例：

```json
{
  "id": "gdp_growth",
  "title": "GDP增速",
  "unit": "%",
  "frequency": "quarterly",
  "range": {
    "type": "1y",
    "start_date": "2025-05-01",
    "end_date": "2026-05-01"
  },
  "series": [
    {
      "name": "名义GDP增速",
      "points": [
        { "date": "2026-03-31", "period_label": "2026Q1", "value": 3.87, "unit": "%" }
      ]
    },
    {
      "name": "实际GDP增速",
      "points": [
        { "date": "2026-03-31", "period_label": "2026Q1", "value": 4.75, "unit": "%" }
      ]
    }
  ]
}
```

失败：

- `400`：`invalid_macro_data_range`
- `503`：`frontend_macro_data_chart_unavailable`

### 4.3 `GET /api/frontend/modules/market-data`

查询参数：

- `tab`：`commodities | precious_metals | stock_market | real_estate`，默认 `commodities`

用途：返回 Market Data 模块元数据、分类标签、时间范围选项和图表定义。房地产分类包含 `second_hand_housing`。

### 4.4 `GET /api/frontend/modules/market-data/charts/{chart_id}`

查询参数：

- `range`：`6m | 1y | 3y | 5y | 10y | 15y | 20y | 25y | 30y | custom`
- `start_date` / `end_date`：自定义范围日期，`YYYY-MM-DD`
- `frequency`：`daily | monthly | yearly`
- `cities`：房地产图表可选，逗号分隔城市名，例如 `北京,上海`

房地产口径说明：`second_hand_housing` 来源字段为 AkShare/国家统计局 70 城二手住宅价格指数；旧版页面显示的是“二手住宅价格指数-同比”的 100 基准指数。当前接口改为 `chart_type: "housing_multi_metric"`，每个城市返回三组序列：

- `{city} 同比`：`二手住宅价格指数-同比 - 100`，单位 `%`
- `{city} 环比`：`二手住宅价格指数-环比 - 100`，单位 `%`
- `{city} 全局走势`：从历史首期前值 `100` 起，用环比百分比逐月复合得到的全局房价走势指数，单位 `指数`

#### 4.4.1 `POST /api/frontend/modules/market-data/sync/{chart_id}`

用途：手动刷新一张 Market Data 图表对应的历史数据。接口仅同步 `{chart_id}` 指定指标，不会连带刷新同分类其他图表，避免单个上游波动阻断仍可用指标。

全球期货同步策略：

- 布伦特、黄金、白银、铜优先读取东方财富全球期货历史，收盘价按字段名解析。
- 东方财富端点异常时，分别回退新浪外盘日线 `OIL`、`XAU`、`XAG`、`CAD`。
- 铜的新浪 `CAD` 回退序列从美元/公吨换算为美元/磅。
- 外部数据源返回空结果时快速失败，保留 `.data/market_data.db` 内上一次可展示历史。

成功：`200`

```json
{
  "ok": true,
  "point_counts": {
    "wti_crude_oil": 7687
  }
}
```

失败：

- `400`：`invalid_market_data_chart_id`
- `503`：`frontend_market_data_sync_failed`

### 4.4.2 `GET /api/frontend/modules/market-data/stocks`

用途：股票市场页读取 A 股全市场股票、ETF 与 LOF 标的列表。服务在本地标的池为空时会尝试通过 AkShare 首次同步股票代码/名称并落库，避免每次搜索都访问外部接口。

查询参数：

- `query`：股票代码、带后缀代码或名称关键字。
- `instrument_type`：`all | stock | etf | lof`，默认 `all`。
- `market_board`：`all | 沪市 | 深市 | 沪市主板 | 深市主板 | 科创板 | 创业板 | 北交所 | 境外`，默认 `all`。ETF/LOF 不再使用 `ETF` 作为市场类型，境外 ETF 归入 `境外`。
- `listing_status`：`all | listed | st | delisted`，默认 `all`。
- `limit` / `offset`：分页参数，`limit` 最大 200。

成功：`200`

```json
{
  "items": [
    {
      "symbol": "000001.SZ",
      "code": "000001",
      "exchange": "SZ",
      "name": "平安银行",
      "instrument_type": "stock",
      "market_board": "深市主板",
      "listing_status": "listed"
    }
  ],
  "total": 1,
  "universe_count": 5238,
  "warning_message": ""
}
```

失败：

- `400`：`invalid_stock_market_filter`
- `503`：`frontend_stock_instruments_unavailable`

### 4.4.3 `GET /api/frontend/modules/market-data/stocks/overview`

用途：返回股票研究工作台顶部的真实市场摘要。指数复用 Push Center 默认宽基注册表，读取 `.data/market_history.db` 最近两个有效点；市场宽度从股票日线分片聚合最近两个交易日的上涨、下跌和平盘家数。
每个指数同时返回 `daily_bars`，供前端点击概览项后下发展示宽基 K 线。该字段复用 Push Center 宽基历史近 5 年收盘与成交量；因历史库不保存完整 OHLC，开盘价使用前一交易日收盘价派生，最高/最低价取开收盘边界。

成功：`200`

```json
{
  "generated_at": "2026-06-10T15:23:45Z",
  "indices": [
    {
      "symbol": "CSI300",
      "display_name": "沪深 300",
      "close": 3921.5,
      "change": 21.5,
      "change_pct": 0.551282,
      "trade_date": "2026-06-09",
      "status": "live",
      "daily_bars": [
        {
          "date": "2026-06-08",
          "open": 3900.0,
          "close": 3900.0,
          "high": 3900.0,
          "low": 3900.0,
          "volume": 1000.0,
          "ma5": null,
          "ma10": null,
          "ma20": null,
          "ma60": null,
          "ma120": null,
          "pe_ttm": null,
          "pb_mrq": null,
          "dividend_yield_ttm": null,
          "total_market_cap": null
        },
        {
          "date": "2026-06-09",
          "open": 3900.0,
          "close": 3921.5,
          "high": 3921.5,
          "low": 3900.0,
          "volume": 1200.0,
          "ma5": null,
          "ma10": null,
          "ma20": null,
          "ma60": null,
          "ma120": null,
          "pe_ttm": null,
          "pb_mrq": null,
          "dividend_yield_ttm": null,
          "total_market_cap": null
        }
      ]
    },
    {
      "symbol": "CSI500",
      "display_name": "中证 500",
      "close": 6088.0,
      "change": -12.0,
      "change_pct": -0.196721,
      "trade_date": "2026-06-09",
      "status": "live"
    },
    {
      "symbol": "CSI1000",
      "display_name": "中证 1000",
      "close": 6740.0,
      "change": 40.0,
      "change_pct": 0.597015,
      "trade_date": "2026-06-09",
      "status": "live"
    },
    {
      "symbol": "SSE",
      "display_name": "上证综指",
      "close": 3242.18,
      "change": 42.18,
      "change_pct": 1.318125,
      "trade_date": "2026-06-09",
      "status": "live"
    },
    {
      "symbol": "SZSE",
      "display_name": "深证成指",
      "close": 10186.45,
      "change": 86.45,
      "change_pct": 0.855941,
      "trade_date": "2026-06-09",
      "status": "live"
    },
    {
      "symbol": "CHINEXT",
      "display_name": "创业板指",
      "close": 2112.6,
      "change": 12.6,
      "change_pct": 0.6,
      "trade_date": "2026-06-09",
      "status": "live"
    },
    {
      "symbol": "HSTECH",
      "display_name": "恒生科技指数",
      "close": 4285.0,
      "change": -15.0,
      "change_pct": -0.348837,
      "trade_date": "2026-06-09",
      "status": "live"
    }
  ],
  "breadth": {
    "trade_date": "2026-06-09",
    "advanced": 3421,
    "declined": 1428,
    "unchanged": 82,
    "total": 4931,
    "status": "live"
  }
}
```

兼容和降级：

- 单个指数少于两个有效点时，该指数返回 `status: "unavailable"` 和空数值，其余项目仍返回。
- `daily_bars` 为兼容新增字段；旧前端可忽略，新前端在字段为空或缺失时展示宽基历史暂无可用数据。
- `indices` 当前按 Push Center 默认宽基注册表顺序返回：`CSI300`、`CSI500`、`CSI1000`、`SSE`、`SZSE`、`CHINEXT`、`HSTECH`；前端应按数组顺序渲染，不依赖固定两项。
- 市场宽度无法聚合时仅 `breadth.status` 为 `unavailable`。
- Service 整体异常时返回 `503 frontend_stock_market_overview_unavailable`。

### 4.4.4 `POST /api/frontend/modules/market-data/stocks/sync-universe`

用途：手动刷新 A 股/ETF/LOF 基础标的池。股票优先来自 AkShare `stock_info_a_code_name`，失败时回退 A 股快照端点；ETF 优先来自 `fund_etf_spot_em`，失败时回退同花顺/新浪 ETF 端点；LOF 优先来自 `fund_lof_spot_em`，失败时回退新浪 `LOF基金` 分类，再以场内基金排行端点兜底。本地表以 `symbol` 幂等 upsert，不删除既有标的。股票、ETF 与 LOF 分段容错，任一来源失败时不阻断另一来源入库，失败详情通过 `warnings` 返回。

成功：`200`

```json
{
  "ok": true,
  "counts": {
    "stock": 5200,
    "etf": 438,
    "lof": 120,
    "total": 5758
  },
  "warnings": []
}
```

失败：仅数据库写入等内部错误返回 `503 frontend_stock_universe_sync_failed`；外部行情源代理失败通常返回 `200` 并在 `warnings` 中说明。

### 4.4.5 `POST /api/frontend/modules/market-data/stocks/refresh-all`

用途：启动“全部标的”后台刷新任务。服务会逐只刷新当前本地上市和 ST 状态股票、ETF、LOF 的近 1 个月日线行情和公司概况；股票额外刷新财务指标，ETF/LOF 不拉取公司财报。该任务异步执行，手动刷新和自动定时刷新共用同一任务状态。服务按上海本地日期做每日限次，同一天最多实际执行一次；重复点击会返回正在运行的任务或 `skipped` 状态。

成功：`202`

```json
{
  "job": {
    "id": "f89f...",
    "status": "running",
    "trigger": "manual",
    "completed": 128,
    "total": 6931,
    "percentage": 2,
    "current_symbol": "000001.SZ",
    "current_label": "平安银行",
    "message": "正在刷新 平安银行。",
    "errors": [],
    "started_at": "2026-06-19T07:30:00Z",
    "finished_at": ""
  }
}
```

失败：`503 frontend_stock_all_refresh_start_failed`

### 4.4.6 `GET /api/frontend/modules/market-data/stocks/refresh-all/latest`

用途：读取最近一次全部标的刷新任务，供前端微型进度条展示手动任务或 15:30 自动任务进度。

成功：`200`

```json
{
  "job": null,
  "state": {
    "last_refresh_date": "2026-06-19",
    "last_refresh_at": "2026-06-19T07:42:00Z",
    "last_trigger": "scheduled"
  }
}
```

### 4.4.7 `GET /api/frontend/modules/market-data/stocks/refresh-all/{job_id}`

用途：读取指定全部标的刷新任务状态。任务状态为 `completed_with_warnings` 时表示部分标的外部数据源失败，服务保留旧数据并在 `errors` 中返回短错误摘要。

失败：

- `404`：任务不存在
- `503`：`frontend_stock_all_refresh_status_failed`

### 4.4.8 后台定时刷新

股票市场服务启动后会在后台检查上海时间 `15:30` 槽位，到点自动触发 `scheduled` 全标的刷新。自动任务和手动任务共用每日限次状态文件 `.data/stock_market_refresh_state.json`，因此当天手动刷新完成后，15:30 不会再次拉取外部数据；反之亦然。

### 4.4.9 `GET /api/frontend/modules/market-data/stocks/{symbol}`

用途：返回选中股票/ETF/LOF 的日级别 K 线数据、公司概况、所属板块、股票属性和财报图表数据。若该标的本地没有任何日线数据，服务会先懒加载近 1 个月日线；只要已有任意日线数据，后续打开不会自动重复拉取，需用户手动刷新。

查询参数：

- `range`：`1m | 3m | 6m | 1y | 3y | 5y | custom`，默认 `1m`。
- `start_date` / `end_date`：自定义日期，`YYYY-MM-DD`。
- `financial_report_type`：`quarterly | yearly`，默认 `quarterly`。

日线同步策略：

- A 股使用 AkShare `stock_zh_a_hist`，ETF 使用 `fund_etf_hist_em`，LOF 使用 `fund_lof_hist_em`。
- A 股日线在东方财富端点失败时回退 `stock_zh_a_hist_tx` / `stock_zh_a_daily`；腾讯接口的 `amount` 手数会转换为统一的 `volume` 股数。ETF 日线在东方财富端点失败时回退 `fund_etf_hist_sina`。
- 本地事实表以 `(symbol, trade_date)` 作为幂等键，刷新同一天只更新，不重复插入。
- 服务会为 MA120 额外拉取起始日前约 220 天缓冲数据，返回 payload 仍只包含用户所选时间跨度。
- 外部接口失败时保留本地已有历史，并在 `sync_state.warning_message` 返回可展示的短提示；服务不会把代理失败的完整 traceback 写入前端响应。

成功：`200`

```json
{
  "instrument": { "symbol": "000001.SZ", "name": "平安银行" },
  "range": { "type": "1m", "start_date": "2026-05-05", "end_date": "2026-06-05" },
  "daily_bars": [
    {
      "date": "2026-06-05",
      "open": 11.2,
      "close": 11.5,
      "high": 11.8,
      "low": 11.1,
      "volume": 1234500,
      "ma5": 11.42,
      "ma10": 11.35,
      "ma20": 11.18,
      "ma60": 10.88,
      "ma120": 10.42,
      "pe_ttm": 5.12,
      "pb_mrq": 0.48,
      "dividend_yield_ttm": 3.26,
      "total_market_cap": 2130.77
    }
  ],
  "profile": {
    "company_name": "平安银行股份有限公司",
    "industry": "银行",
    "sector": "银行",
    "attributes": ["价值股"]
  },
  "financials": {
    "report_type": "quarterly",
    "unit": "亿元",
    "series": [
      { "metric": "revenue", "label": "营业收入", "points": [] },
      { "metric": "expense", "label": "营业支出", "points": [] },
      { "metric": "cash_flow", "label": "经营活动现金流", "points": [] },
      { "metric": "asset", "label": "资产合计", "points": [] },
      { "metric": "liability", "label": "负债合计", "points": [] },
      { "metric": "roe", "label": "ROE", "points": [] },
      { "metric": "revenue_yoy", "label": "营收同比", "points": [] },
      { "metric": "net_profit_yoy", "label": "净利润同比", "points": [] },
      { "metric": "debt_asset_ratio", "label": "资产负债率", "points": [] }
    ]
  }
}
```

估值字段均允许为 `null`。`pe_ttm` 与 `pb_mrq` 单位为倍，
`dividend_yield_ttm` 单位为 `%`，`total_market_cap` 单位为亿元。季度财务新增指标的
`points[].unit` 均为 `%`。本次契约只增加字段和指标序列，不删除或改名现有字段。

股票日线刷新会从东方财富估值历史补充 PE(TTM)、PB(MRQ) 和总市值；股息率(TTM) 基于过去
365 个自然日内已实施且已除息的每股现金分红与当日收盘价计算。附加数据源失败时保留
OHLCV 和本地已有指标，并通过 `sync_state.warning_message` 返回短告警。

失败：

- `400`：`invalid_stock_symbol_or_range`
- `503`：`frontend_stock_detail_unavailable`

### 4.4.10 `POST /api/frontend/modules/market-data/stocks/{symbol}/sync`

用途：手动刷新选中股票/ETF/LOF 在当前时间跨度内的日线数据，并返回刷新后的详情 payload。股票会同时
强制刷新财务指标，确保 ROE、营收同比、净利润同比和资产负债率可以补采最新季度数据；ETF/LOF 不执行
公司财务指标刷新。

请求体：

```json
{
  "range": "1m",
  "start_date": null,
  "end_date": null,
  "financial_report_type": "quarterly"
}
```

成功：`200`，响应同详情接口，并额外包含 `refresh_result`：

```json
{
  "refresh_result": {
    "daily_bars": 162,
    "financial_metrics": 846
  }
}
```

ETF 的 `refresh_result` 仅包含 `daily_bars`。

失败：

- `400`：`invalid_stock_symbol_or_range`
- `503`：`frontend_stock_detail_sync_failed`

### 4.5 Outlook 时间轴接口

#### 4.5.1 `GET /api/frontend/modules/event-outlook`

查询参数：

- `region`：`domestic | international`，默认 `domestic`
- `start_date`：可选，`YYYY-MM-DD`；默认浏览器/服务端当前日期
- `end_date`：可选，`YYYY-MM-DD`；默认起始日期后一年
- `refresh`：可选，传 `1` 时刷新内置科技、时政、财经未来事件种子

用途：返回 Outlook 一级模块的国内/国际时间轴数据。事件持久化在 `.data/events_outlook.db` 的 `timeline_events` 表中，`category` 取值为 `technology | politics | finance`，前端分别以三种颜色展示。

成功：`200`

```json
{
  "generated_at": "2026-05-06T00:00:00Z",
  "module": {
    "id": "event-outlook",
    "title": "Outlook",
    "description": "Forward calendar for technology, policy, and finance events."
  },
  "region": "domestic",
  "tabs": [
    { "value": "domestic", "label": "国内" },
    { "value": "international", "label": "国际" }
  ],
  "range": {
    "start_date": "2026-05-06",
    "end_date": "2027-05-06"
  },
  "resolution_options": [
    { "value": "day", "label": "天" },
    { "value": "week", "label": "周" },
    { "value": "month", "label": "月" }
  ],
  "events": [
    {
      "id": 1,
      "region": "domestic",
      "event_date": "2026-06-23",
      "title": "夏季达沃斯 2026",
      "summary": "世界经济论坛新领军者年会将于 2026 年 6 月 23 日至 25 日在大连举行。",
      "category": "finance",
      "source_name": "World Economic Forum",
      "source_url": "https://www.weforum.org/meetings/annual-meeting-of-the-new-champions-2026/about/",
      "updated_at": "2026-05-06T00:00:00Z"
    }
  ]
}
```

失败：

- `400`：`invalid_event_outlook_payload`
- `503`：`frontend_event_outlook_module_unavailable`

#### 4.5.2 `POST /api/frontend/modules/event-outlook/events`

用途：手动录入一条时间轴事件并写入 SQLite。

请求体：

```json
{
  "region": "domestic",
  "event_date": "2026-09-09",
  "title": "2026 中国国际服务贸易交易会",
  "summary": "服贸会及全球服务贸易峰会窗口。",
  "category": "finance",
  "source_name": "manual",
  "source_url": ""
}
```

成功：`201`，返回 `{ "event": { ... } }`

失败：`400`，`invalid_event_outlook_payload`

#### 4.5.3 `PUT /api/frontend/modules/event-outlook/events/{event_id}`

用途：修改事件标题与摘要，修改后立即持久化。

请求体：

```json
{
  "title": "COMPUTEX 2026 更新",
  "summary": "更新后的事件摘要。"
}
```

成功：`200`，返回 `{ "event": { ... } }`

失败：`400`，`invalid_event_outlook_payload`

### 4.6 Event Insight 导入与任务接口

Event Insight 使用独立前缀，不复用 Outlook 静态日历接口：

```text
/api/frontend/modules/event-insight/*
```

#### 4.6.1 `POST /api/frontend/modules/event-insight/documents/import`

用途：导入事件洞察原始材料，并创建可恢复的 `parse_document` 本地任务。接口在请求线程内只做校验、入库和受控文件复制，不抓取远端 URL 正文，不触发 LLM 抽取。

请求头：

- `Idempotency-Key`：可选；重复请求返回同一个任务。

请求 JSON 支持三种模式：

```json
{
  "mode": "text",
  "title": "存储芯片报价上调",
  "content": "DRAM 合约价上涨，AI 服务器需求支撑内存涨价。"
}
```

```json
{
  "mode": "url",
  "title": "HBM4 量产节奏提前",
  "url": "https://example.com/research/hbm4"
}
```

```json
{
  "mode": "file",
  "title": "研报摘要",
  "fileName": "memory-report.txt",
  "contentType": "text/plain",
  "content": "存储芯片价格继续上涨。"
}
```

文件导入约束：

```text
1. 文件名不得包含路径或 `..`。
2. 支持 .txt/.md/.json/.html/.htm/.pdf。
3. MIME 必须与扩展名匹配。
4. 默认单次内容上限为 5MB。
5. 本地文件复制到受控目录 `.data/event_insight/raw/*`，数据库只保存相对路径。
```

成功：`202`

```json
{
  "jobId": 1,
  "jobType": "parse_document",
  "status": "pending",
  "rawDocumentId": 1,
  "traceId": "event-insight-job-1"
}
```

失败：

- `400`：`invalid_event_insight_import_payload`
- `503`：`event_insight_import_failed`

#### 4.6.2 `GET /api/frontend/modules/event-insight/jobs/{jobId}`

用途：轮询 Event Insight 本地任务状态。

成功：`200`

```json
{
  "id": 1,
  "jobId": 1,
  "jobType": "parse_document",
  "status": "pending",
  "attemptCount": 0,
  "maxAttempts": 3,
  "error": "",
  "payload": {
    "rawDocumentId": 1
  },
  "rawDocumentId": 1,
  "traceId": "event-insight-job-1"
}
```

失败：

- `404`：`event_insight_job_not_found`
- `503`：`event_insight_job_status_failed`

### 4.7 Event Insight 事件工作台接口

Event Insight 事件工作台用于管理已经发生或正在被研究的事实事件，不表示未来日历。Outlook 仍保留为静态未来事件时间线，两者不共用数据表和接口。

#### 4.7.1 `GET /api/frontend/modules/event-insight/events`

用途：分页返回结构化事件列表，默认仅返回 `manualStatus=active` 且未归档事件。

查询参数：

- `keyword`：可选，标题/摘要关键字。
- `status`：`active | ignored | archived | all`，默认 `active`。
- `topicId`：可选，按主题筛选。
- `page` / `pageSize`：默认 `1 / 20`，`pageSize` 最大 100。
- `sortBy` / `sortOrder`：默认 `event_time / desc`。

成功：`200`

```json
{
  "traceId": "event-insight-events-abc123",
  "items": [
    {
      "id": 1,
      "title": "存储芯片报价上调",
      "summary": "DRAM 合约价上涨，AI 服务器需求支撑内存涨价。",
      "eventTime": "2026-05-16T10:30:00+08:00",
      "eventType": "price_change",
      "confidenceScore": 0.82,
      "manualStatus": "active"
    }
  ],
  "page": 1,
  "pageSize": 20,
  "total": 1
}
```

#### 4.7.2 `GET /api/frontend/modules/event-insight/events/{eventId}`

用途：返回事件详情、主题归属和证据链。

成功：`200`，返回 `{ "traceId": "...", "event": { "evidence": [], "topics": [], "entities": [] } }`。P6 起 `evidence` 包含 `startOffset/endOffset/sourceTitle/sourceUrl`，用于在前端核查证据原文位置。

失败：`404`，`event_insight_event_not_found`

#### 4.7.8 事件抽取内部任务

P6 新增本地 `extract_event` 任务处理能力。该任务不新增公开 HTTP 端点，由 worker 或测试服务领取 `processing_job` 中的 `job_type=extract_event` 记录执行。

任务 payload：

```json
{ "rawDocumentId": 1 }
```

处理结果：

```json
{
  "analysisRunId": 1,
  "eventIds": [1]
}
```

失败语义：

- 模型输出非 JSON：任务失败并写入 `analysis_run.error_message`。
- JSON 缺少必填字段：任务失败。
- `evidence.excerpt` 无法在 `raw_document.content_text` 中定位：任务失败，拒绝写入该证据链。

#### 4.7.9 检索、重复候选与规则聚类内部能力

P7 新增 `EventRetrievalService`，当前不新增公开 HTTP 端点，供后续主题溯源页、关系图页或后台任务复用。

能力边界：

- `search_events(query)`：对 active 事件执行中文 n-gram fallback 检索，解决 SQLite FTS5 对中文短词召回弱的问题。
- `generate_duplicate_candidates(source_event_id, threshold)`：只写入 `duplicate_event_candidate`，不自动合并、不删除事件、不修改 `manual_status`。
- `cluster_events(keyword, topic_name)`：创建或复用主题，并把匹配事件写入 `topic_event`；自动规则关联使用 `manual_locked=false`，便于后续人工调整。
- `inspect_vector_runtime()`：仅探测 `sqlite-vec` 可用性；扩展不可用时返回原因，不阻断基础检索。

#### 4.7.10 `GET /api/frontend/modules/event-insight/topics/{topicId}/trace`

用途：返回主题溯源页所需的真实主题、指标、阶段、时间线和当前判断。该接口读取 `topic`、`topic_event`、`event` 与证据链，不调用 LLM，不生成关系图投影。

成功：`200`

```json
{
  "traceId": "event-insight-topic-trace-abc123",
  "topic": { "id": 1, "name": "内存涨价", "summary": "围绕存储芯片供需变化。" },
  "metrics": [
    { "label": "主题事件", "value": "2", "note": "按时间倒序展示", "noteTone": "green" }
  ],
  "stages": [
    { "id": "stage-1", "label": "阶段 01", "title": "存储芯片报价上调", "active": false },
    { "id": "stage-2", "label": "阶段 02 · 当前", "title": "CPO 光模块订单增加", "active": true }
  ],
  "timeline": [
    {
      "id": "event-2",
      "eventId": 2,
      "happenedAt": "2026-05-20T10:30:00+08:00",
      "title": "CPO 光模块订单增加",
      "summary": "海外云厂商资本开支上修。",
      "roleInTopic": "supporting_event",
      "evidenceCount": 0,
      "evidence": []
    }
  ],
  "currentJudgement": {
    "title": "阶段 02：CPO 光模块订单增加",
    "summary": "围绕存储芯片供需变化。",
    "clues": ["继续补充交叉证据"]
  }
}
```

失败：

- `404`：`event_insight_topic_not_found`
- `503`：`event_insight_topic_trace_failed`

#### 4.7.11 `GET /api/frontend/modules/event-insight/graph`

用途：返回事件关系图的 SQLite 投影。该接口以事件列表中的事实事件为输入，不依赖主题溯源；默认会把通过质量审核的 active 事件投入事件网络，并用轻量规则与既有事件自动聚类、生成 `event_relation` 关系边。不调用 LLM，不依赖 Neo4j。

查询参数：

- `topicId`：兼容旧查询的可选过滤参数；新前端不再传入。传入时只返回该主题内事件节点和这些节点之间的关系边；主题不存在返回 404。

质量审核规则：

- `manual_status=active` 且未归档。
- `confidence_score >= 0.6`。
- `evidence_level <> D`。
- 通过审核的 pending 事件会在图谱读取时更新为 `graph_status=relation_built` 或 `clustered`。

成功：`200`

```json
{
  "traceId": "event-insight-graph-abc123",
  "nodes": [
    {
      "id": "event-1",
      "eventId": 1,
      "kind": "price_change",
      "title": "存储芯片报价上调",
      "happenedAt": "2026-05-16T10:30:00+08:00",
      "confidence": "高可信 · 82",
      "confidenceTone": "green",
      "summary": "DRAM 合约价上涨，AI 服务器需求支撑内存涨价。",
      "left": "12%",
      "top": "22%"
    }
  ],
  "edges": [
    {
      "id": "relation-1",
      "sourceNodeId": "event-1",
      "targetNodeId": "event-2",
      "type": "cause",
      "summary": "内存涨价推升光模块订单预期。",
      "strengthScore": 0.73,
      "confidenceScore": 0.81,
      "left": "25%",
      "top": "35%",
      "width": "34%",
      "rotate": "18deg"
    }
  ],
  "selectedNodeId": "event-1"
}
```

失败：

- `404`：`event_insight_topic_not_found`
- `503`：`event_insight_graph_failed`

#### 4.7.3 `PUT /api/frontend/modules/event-insight/events/{eventId}`

用途：写入人工字段覆盖。接口不会改写原始事实字段，而是追加 `event_field_override` 和 `event_operation_log`。

请求体：

```json
{
  "title": "DRAM 合约价延续上涨",
  "summary": "多来源确认内存涨价。",
  "eventType": "price_change",
  "confidenceScore": 0.9,
  "reason": "人工确认"
}
```

成功：`200`，返回更新后的展示事件。

失败：

- `400`：`invalid_event_insight_event_payload`
- `404`：`event_insight_event_not_found`

#### 4.7.4 `POST /api/frontend/modules/event-insight/events/{eventId}/ignore`

用途：将事件标记为 `ignored`，默认列表不再返回该事件。

请求体：`{ "reason": "重复新闻或低价值噪声" }`

成功：`200`

失败：`404`，`event_insight_event_not_found`

#### 4.7.5 `POST /api/frontend/modules/event-insight/topics`

用途：创建或复用同名主题。

请求体：`{ "name": "内存涨价", "summary": "围绕存储芯片供需变化。" }`

成功：`201`

失败：`400`，`invalid_event_insight_topic_payload`

#### 4.7.5.1 `GET /api/frontend/modules/event-insight/topics`

用途：返回前端主题选择器可用的未归档主题列表，默认按 `updated_at desc, id desc` 排序。

成功：`200`

```json
{
  "traceId": "event-insight-topics-abc123",
  "items": [
    {
      "id": 2,
      "name": "光模块景气",
      "summary": "围绕光模块订单变化。",
      "lifecycleStage": "noise",
      "heatScore": 0,
      "roleInTopic": "",
      "relevanceScore": 0,
      "manualLocked": false
    }
  ],
  "total": 1
}
```

失败：`503`，`event_insight_topics_unavailable`

#### 4.7.6 `POST /api/frontend/modules/event-insight/events/{eventId}/link-topic`

用途：将事件关联到主题。

请求体：`{ "topicId": 1, "roleInTopic": "key_catalyst" }`

成功：`200`

失败：

- `400`：`invalid_event_insight_topic_link_payload`
- `404`：`event_insight_event_or_topic_not_found`

#### 4.7.7 `POST /api/frontend/modules/event-insight/events/batch-action`

用途：批量忽略或批量关联主题。接口采用部分成功语义，单条失败不会回滚其他事件。

请求体：

```json
{
  "eventIds": [1, 9999],
  "action": "ignore",
  "params": { "reason": "批量忽略" }
}
```

成功：`200`

```json
{
  "traceId": "event-insight-batch-abc123",
  "succeededEventIds": [1],
  "failedItems": [{ "eventId": 9999, "error": "event_not_found" }]
}
```

失败：`400`，`invalid_event_insight_batch_action`

### 4.8 `GET /api/frontend/modules/push`

查询参数：

- `refresh`（可选）
- `include_preview`（可选，`0` 可跳过预览构建）

成功：

- `200`：返回 Push Center 工作区 payload
- 响应中带 `refresh_after_ms`，前端可按此轮询

失败：`503`，`frontend_push_module_unavailable`

### 4.9 System LLM Settings 接口

用途：统一管理事件洞察后续抽取、聚类、摘要和关系判断使用的模型配置。接口不会返回明文 API Key。

#### 4.9.1 `GET /api/system/llm/providers`

成功：`200`

```json
{
  "providers": [
    {
      "id": 1,
      "name": "主分析模型",
      "providerType": "openai_compatible",
      "baseUrl": "https://api.example.com/v1",
      "modelName": "analysis-model",
      "timeoutSeconds": 90,
      "supportsStructuredOutput": true,
      "supportsEmbeddings": false,
      "enabled": true,
      "apiKeyConfigured": true,
      "apiKeyPreview": "sk-...alue"
    }
  ]
}
```

#### 4.9.2 `POST /api/system/llm/providers`

请求体：

```json
{
  "name": "主分析模型",
  "providerType": "openai_compatible",
  "baseUrl": "https://api.example.com/v1",
  "modelName": "analysis-model",
  "apiKey": "sk-***",
  "timeoutSeconds": 90
}
```

成功：`201`，返回脱敏后的 `{ "provider": { ... } }`。

失败：`400`，`invalid_llm_provider_payload`

#### 4.9.3 `PUT /api/system/llm/providers/{id}`

用途：更新 provider 配置；请求体缺少 `apiKey` 时保留旧密钥。

成功：`200`

失败：

- `400`：`invalid_llm_provider_payload`
- `404`：`llm_provider_not_found`

#### 4.9.4 `POST /api/system/llm/providers/{id}/disable`

用途：禁用 provider。若 provider 被任务映射引用，返回 `409 provider_in_use`。

#### 4.9.5 `POST /api/system/llm/providers/{id}/test`

用途：测试 provider 连接。接口会使用已保存的脱敏后端配置发起一次短模型调用，验证 provider、baseUrl、model 与 API Key 是否可用。

成功：`200`，返回 `{ "ok": true, "detail": "连接测试成功：..." }`。

连接失败：`200`，返回 `{ "ok": false, "detail": "连接测试失败：..." }`；`detail` 不包含明文 API Key。

连接测试会写入 `llm_call_log`，日志只保存脱敏后的请求摘要和响应摘要，不保存 API Key、完整请求头或完整 prompt。

#### 4.9.6 `GET /api/system/llm/task-configs`

用途：读取任务到 provider/model 的映射。

#### 4.9.7 `PUT /api/system/llm/task-configs/{taskType}`

请求体：

```json
{
  "providerId": 1,
  "modelName": "analysis-model",
  "temperature": 0.2,
  "maxTokens": 800
}
```

成功：`200`，返回 `{ "taskConfig": { ... } }`。

#### 4.9.8 `GET /api/system/llm/call-logs`

用途：查看 LLM 真实调用日志，供 System 页面核验连接测试是否实际发起。

参数：

- `taskType`：可选，例如 `connection_test`
- `limit`：可选，默认 `20`，最大 `100`

成功：`200`

```json
{
  "items": [
    {
      "id": 1,
      "taskType": "connection_test",
      "providerId": 1,
      "providerName": "主分析模型",
      "providerType": "openai_compatible",
      "modelName": "analysis-model",
      "status": "succeeded",
      "requestPreview": "system: ... | user: ...",
      "responsePreview": "OK",
      "errorMessage": "",
      "createdAt": "2026-06-03T08:00:00Z"
    }
  ]
}
```

### 4.10 System RSS Settings 接口

用途：在 System 页面独立 RSS 源配置 Tab 中管理 RSS 源和每日抓取时间，RSS 条目会接入 Event Insight 的 `raw_document / event / evidence` 链路。首次读取时，后端会把 `src/news/fetcher.py` 中原有写死的默认 RSS 源导入 `rss_source_config`，后续以数据库配置为准。

#### 4.10.1 `GET /api/system/rss/sources`

成功：`200`

```json
{
  "sources": [
    {
      "id": 1,
      "name": "AI 财经观察",
      "url": "https://example.com/rss.xml",
      "language": "zh",
      "category": "finance",
      "enabled": true,
      "fetchTime": "06:30",
      "maxItems": 20,
      "lastFetchedAt": null
    }
  ],
  "scheduler": {
    "enabled": true,
    "timezone": "Asia/Shanghai",
    "dailyFetchTime": "06:30"
  }
}
```

#### 4.10.2 `POST /api/system/rss/sources`

创建 RSS 源。失败：`400 invalid_rss_source_payload`。

#### 4.10.3 `PUT /api/system/rss/sources/{id}`

更新 RSS 源。失败：`404 rss_source_not_found`。

#### 4.10.4 `DELETE /api/system/rss/sources/{id}`

删除 RSS 源。实现为软删除：设置 `enabled=false` 与 `disabled_at`，列表接口不再返回该源，历史事件来源仍可审计。失败：`404 rss_source_not_found`。

#### 4.10.5 `POST /api/system/rss/sources/{id}/disable`

兼容旧前端的禁用接口。新 UI 使用 `DELETE /api/system/rss/sources/{id}`。

#### 4.10.6 `POST /api/system/rss/sources/{id}/fetch`

手动抓取 RSS 源，成功后将新增条目写入 Event Insight 事件列表。

成功：`200`

```json
{
  "importedCount": 1,
  "skippedCount": 0,
  "fetchedAt": "2026-06-03T08:00:00Z"
}
```

#### 4.10.7 `PUT /api/system/rss/scheduler`

保存每日 RSS 抓取配置。

## 5. Push 控制接口

### 5.1 `PUT /api/push/config`

用途：保存推送配置并返回最新模块 payload。

请求体（前端当前发送）：

```json
{
  "config": {
    "selected_module_ids": ["market"],
    "report_style": "newspaper",
    "market_chart_range": "1y",
    "email": {
      "enabled": true,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "use_tls": true,
      "username": "",
      "password": "",
      "from_address": "",
      "to_addresses": ""
    },
    "schedules": []
  }
}
```

成功：`200`

失败：`400`

```json
{"error":"push_config_update_failed"}
```

### 5.2 `POST /api/push/preview`

用途：按草稿配置生成预览，不要求持久化。`refresh_data=false` 时只使用本地已保留历史重绘；`refresh_data=true` 时先刷新必要数据再重绘。

请求体：

```json
{
  "config": {
    "market_chart_range": "1y"
  },
  "refresh_data": false
}
```

`market_chart_range` 支持 `3m`、`6m`、`1y`、`2y`、`3y`。旧配置缺少该字段时按 `1y` 处理。

成功：`200`

失败：`400`

```json
{"error":"push_preview_failed"}
```

### 5.3 `POST /api/push/market-chart-refresh`

用途：启动 Push preview 宽基指数图表全量刷新。服务会按草稿中的 `market_chart_range` 逐指数拉取所选窗口的收盘数据，按日期写入 SQLite 并保留既有历史，再基于刷新后的 MA20 重绘预览。

请求体：同 `config` 包装结构。

成功：`202`

```json
{
  "job": {
    "id": "f89f...",
    "status": "running",
    "completed": 2,
    "total": 6,
    "percentage": 33,
    "current_symbol": "CSI500",
    "current_label": "中证 500",
    "message": "正在刷新 中证 500。",
    "errors": [],
    "preview": null
  }
}
```

失败：`400`

### 5.4 `GET /api/push/market-chart-refresh/{job_id}`

用途：查询宽基指数图表刷新进度。任务完成后 `preview` 返回重绘后的预览；部分指数上游异常时，状态为 `completed_with_warnings`，并继续使用对应指数上次可用历史。

成功：`200`

失败：

- `404`：任务不存在
- `400`：状态读取失败

### 5.5 `POST /api/push/trigger`

用途：触发一次推送发送。

请求体：同 `config` 包装结构。

成功：

- `200`：发送结果成功
- `502`：服务执行了触发但结果失败（`ok=false`）

失败：`400`

```json
{"error":"push_trigger_failed"}
```

定时推送会在实际发送前按“任务 ID + 计划时区本地分钟”进行跨进程原子抢占。即使同时运行多个
FastAPI 实例，同一计划槽位也只允许一个实例执行发送。

## 6. 错误与兼容性约定

- 错误响应统一至少包含 `error` 字段。
- 前端调用层对 `!response.ok` 抛错，错误消息包含 HTTP 状态码。
- Push Center 接口变更必须同步更新 `frontend/src/features/push/**`、相关测试与 `CHANGELOG.md`。
