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
| `/event-outlook` | GET | Event Outlook SPA 入口，国内/国际时间轴 |
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

### 4.5 Event Outlook 时间轴接口

#### 4.5.1 `GET /api/frontend/modules/event-outlook`

查询参数：

- `region`：`domestic | international`，默认 `domestic`
- `start_date`：可选，`YYYY-MM-DD`；默认浏览器/服务端当前日期
- `end_date`：可选，`YYYY-MM-DD`；默认起始日期后一年
- `refresh`：可选，传 `1` 时刷新内置科技、时政、财经未来事件种子

用途：返回 Event Outlook 一级模块的国内/国际时间轴数据。事件持久化在 `.data/events_outlook.db` 的 `timeline_events` 表中，`category` 取值为 `technology | politics | finance`，前端分别以三种颜色展示。

成功：`200`

```json
{
  "generated_at": "2026-05-06T00:00:00Z",
  "module": {
    "id": "event-outlook",
    "title": "Event Outlook",
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

Event Insight 使用独立前缀，不复用 Event Outlook 静态日历接口：

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

Event Insight 事件工作台用于管理已经发生或正在被研究的事实事件，不表示未来日历。Event Outlook 仍保留为静态未来事件时间线，两者不共用数据表和接口。

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

成功：`200`，返回 `{ "traceId": "...", "event": { "evidence": [], "topics": [] } }`

失败：`404`，`event_insight_event_not_found`

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

## 6. 错误与兼容性约定

- 错误响应统一至少包含 `error` 字段。
- 前端调用层对 `!response.ok` 抛错，错误消息包含 HTTP 状态码。
- Push Center 接口变更必须同步更新 `frontend/src/features/push/**`、相关测试与 `CHANGELOG.md`。
