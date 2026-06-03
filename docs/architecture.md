# 架构与模块边界

本文档定义 `ai-news-bot` 当前架构、模块职责、依赖方向和演进边界。

## 1. 总体架构

项目当前是“前后端分离 + 聚合服务”的形态：

- 前端：`frontend/`（Vite + React + TypeScript）
- 后端：`src/app/web/fastapi_app.py`（FastAPI）
- 领域与服务：`src/domain/`、`src/services/`
- 数据源抽象：`src/providers/`
- 推送链路：`src/services/push_center_service.py` + `src/services/push_report_service.py` + `src/notifiers/`
- 事件洞察事实库：`.data/event_insight.db` + `src/services/event_insight_repository.py`

运行入口：

- `python main.py web`：启动 Web
- `python main.py push`：执行推送任务

## 2. 模块分层与职责

### 2.1 Web 入口层（App Layer）

路径：`src/app/web/`

职责：

- 定义 HTTP 路由和状态码
- 组装服务并返回前端可消费的 payload
- 提供 SPA 静态资源托管与路由兜底

关键文件：

- `fastapi_app.py`：接口定义与错误处理
- `frontend_payload.py`：后端领域模型 -> 前端 payload 适配
- `spa_assets.py`：SPA 入口与静态资源探测

边界：

- 不承担业务计算细节
- 仅调用 `services` 层

### 2.2 服务编排层（Service Layer）

路径：`src/services/`

职责：

- 组合多数据域结果，形成统一快照
- 缓存与后台刷新（DashboardService）
- 推送配置、预览、触发、调度（PushCenterService）

关键服务：

- `DashboardService`
  - 输出 dashboard snapshot
  - 支持按模块独立构建：news/macro/market/events/status
  - 支持 `news_mode` 与 `force_refresh`
- `PushCenterService`
  - 管理 `.data/push_center*.json`
  - 生成预览、发送邮件、定时任务执行

边界：

- 不直接依赖前端组件
- 通过 provider contract 访问外部数据

### 2.3 领域模型层（Domain Layer）

路径：`src/domain/`

职责：

- 定义领域实体、枚举、结构化结果
- 表达业务含义（宏观指标、市场信号、事件展望、新闻条目）

边界：

- 不感知 Web 路由
- 不感知前端展示细节

### 2.4 Provider 抽象层（Provider Layer）

路径：`src/providers/`

职责：

- 统一外部源契约（news/search/macro/market/research）
- 提供主源 + fallback + sample 的降级组合

契约定义：`src/providers/contracts.py`

边界：

- 对上只暴露标准协议，不泄露第三方 API 细节

### 2.5 Repository 层（Persistence Layer）

路径：`src/services/*_repository.py`、`src/services/*_store.py`

职责：

- 管理本地 SQLite 连接、migration、幂等写入和查询
- 保持 IO 与业务编排分离
- 通过显式方法向 Service 层暴露事实数据

Event Insight 约束：

- `.data/event_insight.db` 是事件洞察独立事实库
- `schema_migration` 记录 Event Insight 自身 migration
- 每个 Repository 连接必须启用 `PRAGMA foreign_keys=ON` 与 `PRAGMA journal_mode=WAL`
- 原始材料和事件 FTS 索引由 SQLite trigger 同步
- Neo4j 仅作为后续可重建投影，不是事实来源

### 2.6 前端展示层（Frontend SPA）

路径：`frontend/src/`

职责：

- 路由、页面与可视化交互
- 通过 `features/*/api` 调用后端接口
- 通过 `features/*/model/*-adapter.ts` 做响应适配

边界：

- 不直接拼装后端复杂业务逻辑
- 尽量不依赖后端内部字段命名（通过 adapter 隔离）

## 3. 依赖方向（必须遵守）

推荐依赖方向：

`frontend -> app/web(api) -> services -> providers/contracts -> external sources`

以及：

`services -> domain`

禁止方向：

- `domain -> services`
- `providers -> frontend`
- `app/web -> frontend 业务逻辑`

## 4. 核心运行流

### 4.1 仪表盘页面流

1. 前端请求 `/api/frontend/modules/*` 或 `/api/frontend/dashboard`
2. FastAPI 调用 `DashboardService`
3. Service 调用各模块服务与 provider
4. `frontend_payload.py` 组装统一响应
5. 前端 adapter 转为视图模型

### 4.2 推送流

1. 前端请求 `/api/frontend/modules/push`
2. 更新配置：`PUT /api/push/config`
3. 预览：`POST /api/push/preview`，按 `market_chart_range` 使用本地历史重绘或主动刷新后重绘
4. 宽基指数全量刷新：`POST /api/push/market-chart-refresh`，按当前范围抓取并按日期 `upsert`，不删除更早历史
5. 触发：`POST /api/push/trigger`
6. 服务写入 `.data/logs/push_center/...` 日志

## 5. 模块边界清单

- `news`
  - 负责新闻聚合与分类（tech/finance/policy）
  - 可带 `news_mode`
- `macro`
  - 负责宏观指标快照与历史点
- `market`
  - 负责指数、MA20、fishbowl 信号
- `events`
  - 负责未来事件窗口与官方链接
- `status`
  - 负责数据健康状态与覆盖说明
- `push`
  - 负责推送配置、预览、执行和调度状态
- `event-outlook`
  - 负责未来事件静态日历，继续使用既有 `timeline_events`、`EventsOutlookService`、`EventsOutlookStore` 和 `/api/frontend/modules/event-outlook`
- `event-insight`
  - 负责已发布/导入材料的证据发现、事件归纳、主题溯源和关系构建
  - 使用独立 `.data/event_insight.db`，不得复用静态日历表

## 6. Event Insight 数据边界

Event Insight P2 已建立独立 SQLite 地基：

```text
.data/event_insight.db
  schema_migration
  scan_batch / analysis_run
  raw_document / raw_document_fts
  event / event_fts
  event_source / evidence / event_evidence
  entity / entity_alias / event_entity
  topic / topic_event
  event_relation / relation_evidence
  event_operation_log / event_field_override
  duplicate_event_candidate
  processing_job / processing_job_attempt
  graph_sync_outbox / graph_projection_state
  llm_provider_config / llm_task_config / llm_call_log
```

边界规则：

```text
1. SQLite 是事实主库。
2. FTS5 负责基础全文检索，P7 通过 EventRetrievalService 增加中文 n-gram fallback。
3. 人工校正写入 event_field_override，不直接覆盖模型事实。
4. 重复事件以 duplicate_event_candidate 记录候选，不物理删除。
5. 图谱同步通过 graph_sync_outbox 解耦，Neo4j 后续可从 SQLite 重建。
```

P3 新增材料导入与本地任务队列：

```text
Controller:
  src/app/web/event_insight_routes.py
  - POST /api/frontend/modules/event-insight/documents/import
  - GET /api/frontend/modules/event-insight/jobs/{jobId}

Service:
  src/services/event_insight_import_service.py
  - 校验 text/url/file JSON 导入
  - 生成内容 hash 和幂等键
  - 复制受控本地文件
  - 创建 parse_document job

  src/services/event_insight_job_service.py
  - 创建幂等任务
  - 查询任务状态
  - 领取任务租约
  - 失败重试和 attempt 日志

Repository:
  src/services/event_insight_repository.py
  - processing_job / processing_job_attempt 读写
  - raw_document 查询和 FTS 同步
```

导入边界：

```text
1. URL 导入只保存 URL 元信息，不在 HTTP 请求线程抓取远端正文。
2. 文件导入只保存受控相对路径，禁止路径穿越。
3. P3 创建 parse_document 任务，但不执行事件抽取、Embedding、聚类或图谱同步。
4. 后续 worker 可以通过 claim_next_job 获取带租约的任务，超时后允许恢复领取。
```

P5 新增统一 LLM Runtime：

```text
Controller:
  src/app/web/llm_settings_routes.py
  - /api/system/llm/providers*
  - /api/system/llm/task-configs*

Service:
  src/services/llm_config_service.py
  - 保存 provider 配置
  - 本地加密 API Key
  - 对前端响应脱敏
  - 阻止禁用已被任务映射引用的 provider

  src/services/llm_task_router.py
  - 按 task_type 解析 provider/model/temperature/max_tokens
  - 后续 P6/P8/P9 必须通过该路由调用模型

Provider:
  src/llm_providers/openai_compatible_provider.py
  - 统一 OpenAI-compatible Chat Completions / Embeddings 调用
  - ArkResearchProvider 也通过该 factory 构建 client
```

安全边界：

```text
1. API Key 只在写入请求中出现，列表/详情/测试响应不返回明文。
2. `llm_provider_config.encrypted_api_key` 存储本地加密密文。
3. 禁止在日志中输出密钥或完整请求头。
4. P5 不包含事件抽取 prompt，只建立模型配置和任务路由。
```

P6 新增事件抽取链路：

```text
src/services/event_extraction_service.py
  - 通过 LlmTaskRouter 调用 task_type=event_extraction
  - 校验模型 JSON 输出和必填字段
  - evidence.excerpt 必须能在 raw_document.content_text 中定位
  - 写入 analysis_run / event / event_source / evidence / event_evidence / entity / event_entity / llm_call_log
  - 可领取 processing_job 中的 extract_event 任务并标记成功/失败
```

抽取边界：

```text
1. 抽取只处理已入库 raw_document，不直接抓取远端 URL。
2. 证据链必须引用原文连续片段，禁止模型改写证据。
3. P6 不执行相似搜索、自动去重、主题生成或图谱投影。
```

P7 新增检索、重复候选与规则聚类链路：

```text
src/services/event_retrieval_service.py
  - search_events: 使用中文 n-gram fallback 召回 active 事件
  - generate_duplicate_candidates: 写入 duplicate_event_candidate
  - cluster_events: 创建/复用 topic 并写入 topic_event

src/services/sqlite_vec_loader.py
  - 探测 sqlite-vec 扩展可用性
  - 不可用时只返回状态，不影响 n-gram 基础检索
```

检索边界：

```text
1. P7 不自动确认重复事件，不修改 manual_status。
2. P7 不删除或合并事件，只生成可审核 candidate。
3. 规则聚类只写 topic_event，manual_locked=false，保留人工调整空间。
4. sqlite-vec 是可选增强能力，未安装时不能阻断事件列表、候选生成或聚类。
```

## 7. 状态与降级策略

- Provider 层支持 `live / degraded / unavailable`
- Service 层支持 sample fallback
- Web 层在模块冷启动阶段可返回 `202 + module.loading=true + refresh_after_ms`
- 前端根据 `refresh_after_ms` 自动轮询或用户手动刷新

## 8. 演进建议

- 新模块接入时，优先按顺序新增：
  1. domain model
  2. provider contract/实现
  3. service 聚合
  4. api payload builder
  5. frontend adapter/page
  6. 对应测试与文档
- 若替换外部源，优先在 provider 层处理，避免侵入 service 与 frontend。
