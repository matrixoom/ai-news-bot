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

- `tab`：`gdp | credit | leverage | prices`，默认 `gdp`

用途：返回 Macro Data 模块元数据、子标签、时间范围选项和当前分类下的图表定义。

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

- `range`：`6m | 1y | 3y | 5y | 10y | custom`，默认 `1y`
- `start_date`：自定义范围起始日期，`YYYY-MM-DD`
- `end_date`：自定义范围结束日期，`YYYY-MM-DD`

用途：按单张图表读取 SQLite 中对应指标表的数据。8 个指标分别持久化在 `.data/macro_data.db` 的独立事实表中，例如 `macro_nominal_gdp`、`macro_cpi`。`gdp_growth` 为派生图表，不新增事实表，服务层会基于 `macro_nominal_gdp` 与 `macro_real_gdp` 计算同比增速并返回两条序列。

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

### 4.3 `GET /api/frontend/modules/push`

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

用途：按草稿配置生成预览，不要求持久化。

请求体：同 `config` 包装结构。

成功：`200`

失败：`400`

```json
{"error":"push_preview_failed"}
```

### 5.3 `POST /api/push/trigger`

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
