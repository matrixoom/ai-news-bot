# 接口契约（API Contract）

本文档描述前端与后端当前约定的 HTTP 接口、关键参数、响应语义和错误约定。

## 1. 约定总览

- Base URL：`http://127.0.0.1:8000`
- 返回格式：JSON（除页面入口与错误 HTML）
- 关键查询参数：
  - `news_mode=hybrid|api|upstream`
  - `refresh=true|false`
- 模块加载中语义：
  - HTTP `202`
  - `module.loading = true`
  - `refresh_after_ms` 提示前端重试间隔

## 2. 页面与健康接口

| 路径 | 方法 | 说明 |
| --- | --- | --- |
| `/` | GET | SPA 可用时重定向到 `/dashboard`，否则回退 legacy 页面 |
| `/legacy` | GET | 旧版服务端渲染页面 |
| `/healthz` | GET | 健康检查，返回 `{"status":"ok"}` |

## 3. 仪表盘聚合接口

### 3.1 `GET /api/dashboard`

用途：旧结构聚合快照（兼容接口）。

查询参数：

- `news_mode`（可选）
- `refresh`（可选，true 时强制刷新）

成功：`200`

失败：`503`，示例：

```json
{"error":"dashboard_unavailable"}
```

### 3.2 `GET /api/frontend/dashboard`

用途：前端聚合快照（推荐给 SPA）。

查询参数同上。

成功：`200`

关键响应字段：

- `generated_at`
- `news_mode`
- `news_mode_options`
- `upstream_service_status`
- `title` / `subtitle` / `coverage_note`
- `news_sections` / `macro_sections` / `market_sections` / `event_sections`
- `data_status`

失败：`503`

```json
{"error":"frontend_dashboard_unavailable"}
```

## 4. 模块化接口（`/api/frontend/modules/*`）

### 4.1 通用约定

- 支持 `refresh` 查询参数（部分模块）
- status 支持 `news_mode`
- News / Macro / Market / Events 的独立模块接口已移除；对应顶层页面统一从 `/api/frontend/dashboard` 的 `news_sections`、`macro_sections`、`market_sections`、`event_sections` 取数。
- 典型结构：

```json
{
  "generated_at": "2026-04-01T06:00:00Z",
  "module": {
    "id": "news",
    "label": "...",
    "status": "live|degraded|sample|unavailable|loading",
    "loading": false,
    "details": []
  }
}
```

### 4.2 `GET /api/frontend/modules/status`

查询参数：

- `news_mode`（可选）
- `refresh`（可选）

成功：`200` 或 `202`

失败：`503`，`frontend_status_module_unavailable`

### 4.3 `GET /api/frontend/modules/push`

查询参数：`refresh`（可选）

成功：

- `200`：返回 push 工作区 payload
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

- `200`：`result.ok=true` 或至少有可用发送结果
- `502`：服务执行了触发但结果失败（`ok=false`）

失败：`400`

```json
{"error":"push_trigger_failed"}
```

## 6. 错误与兼容性约定

- 错误响应统一至少包含 `error` 字段。
- 前端调用层对 `!response.ok` 抛错，错误消息包含 HTTP 状态码。
- 若新增字段：应保持向后兼容，不移除既有关键字段。
- 若必须 breaking：需同步更新
  - `frontend/src/features/*/model/*.types.ts`
  - `frontend/src/features/*/model/*-adapter.ts`
  - 相关测试
  - `CHANGELOG.md`

## 7. 前端当前依赖的关键字段

- 全局：`generated_at`
- 模块：`module.id`、`module.status`、`module.loading`、`module.details`
- 自动刷新：`refresh_after_ms`
- News Mode：`news_mode`、`news_mode_options`
- Push：`preview`、`recent_runs`、`result`

建议：任何接口改造前，先 grep 检查前端依赖引用，再修改契约。
