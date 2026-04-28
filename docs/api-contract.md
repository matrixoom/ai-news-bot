# 接口契约（API Contract）

本文档描述当前仍对前端开放的 HTTP 接口。Dashboard、News、Macro、Market、Events 页面与聚合 API 已按需求移除；Push Center 相关后端逻辑保留。

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
| `/push` | GET | Push Center SPA 入口 |
| `/status` | GET | Status SPA 入口 |
| `/settings` | GET | Settings SPA 入口 |
| `/healthz` | GET | 健康检查，返回 `{"status":"ok"}` |

已移除：`/dashboard`、`/news`、`/macro`、`/market`、`/events`、`/legacy`。

## 3. 已移除的聚合与模块接口

以下接口不再对前端提供服务，预期返回 `404`：

- `GET /api/dashboard`
- `GET /api/frontend/dashboard`
- `GET /api/frontend/modules/news`
- `GET /api/frontend/modules/macro`
- `GET /api/frontend/modules/market`
- `GET /api/frontend/modules/events`

说明：Push Center 日报生成仍会在后端内部复用必要的数据快照能力，但这些能力不再作为 Dashboard/News/Macro/Market/Events 页面 API 暴露。

## 4. 保留模块接口

### 4.1 `GET /api/frontend/modules/status`

查询参数：

- `news_mode`（可选，兼容旧调用）
- `refresh`（可选）

成功：`200` 或 `202`

失败：`503`，`frontend_status_module_unavailable`

### 4.2 `GET /api/frontend/modules/push`

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
