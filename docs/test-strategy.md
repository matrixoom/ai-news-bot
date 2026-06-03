# 测试与回归策略

本文档定义本项目的测试分层、回归门禁和发布前检查策略。

## 1. 测试目标

- 保证“可运行”优先：Web、模块接口、推送链路不回归。
- 保证“可降级”可验证：live 源失败时仍能提供 sample/fallback。
- 保证“可演进”安全：接口契约变化可被测试及时发现。

## 2. 测试分层

### 2.1 单元与模块测试（后端）

路径：`tests/test_task*.py`、`tests/test_*.py`

关注点：

- provider 合同与降级策略
- dashboard service 聚合逻辑
- macro data SQLite 分表、时间范围解析与 API 契约
- market data 单图刷新隔离、全球期货收盘列解析与双源回退
- push center 配置、预览、触发逻辑、宽基指数时间范围与历史保留
- event insight SQLite migration、外键、FTS trigger、人工覆盖、重复候选和 graph outbox 幂等
- event insight 材料导入 API、processing_job 幂等、租约恢复、attempt 日志和文件路径安全
- 历史文档校验类 / demo 类测试已归档到 `to_delete/tests/`

### 2.2 集成测试（后端 API）

重点文件：`tests/test_task09_integration_suite.py`

关注点：

- `/api/dashboard` 是否返回完整核心模块
- 推送报告是否复用 dashboard snapshot

### 2.3 前端测试（SPA）

路径：`frontend/src/**/__tests__/`

关注点：

- 路由壳、query 参数与 `news_mode` 保留
- 页面渲染和关键交互（包括侧栏折叠/导航折叠等）
- Macro Data 分类子标签、图表卡片、自定义时间范围和就业年度指标页
- push 页面行为（设置弹窗、保存配置、范围切换本地重绘、全量刷新、预览、触发）

## 3. 回归门禁（建议最小集合）

按改动范围执行，至少通过对应门禁：

### 3.1 Web/API 相关改动

```powershell
uv run python -m pytest tests/test_task03_web_app_shell.py tests/test_task09_integration_suite.py -q
```

### 3.2 News / Provider 策略改动

```powershell
uv run python -m pytest tests/test_task02_provider_strategy.py tests/test_task04_news_pipeline.py tests/test_task04_newsnow_integration.py -q
```

### 3.3 Macro / Market / Events 改动

```powershell
uv run python -m pytest tests/test_macro_data_module.py -q
uv run python -m pytest tests/test_market_data_module.py -q
uv run python -m pytest tests/test_task05_macro_monitoring.py tests/test_task06_market_models.py tests/test_task07_events_outlook.py -q
```

### 3.4 Push 相关改动

```powershell
uv run python -m pytest tests/test_push_workflow.py tests/test_push_center_api.py tests/test_push_email_notifier.py -q
```

### 3.5 Event Insight 数据层改动

```powershell
uv run python -m pytest tests/test_event_insight_repository.py tests/test_event_outlook_timeline.py -q
```

覆盖点：

```text
1. 001_event_insight_core migration 幂等。
2. SQLite 连接启用 foreign_keys 与 WAL。
3. 原始材料和事件 FTS 插入、更新、软归档同步。
4. event_field_override 独立保存人工覆盖，不改写模型事实。
5. duplicate_event_candidate 保留来源事件、候选事件和方法。
6. graph_sync_outbox 通过 idempotency_key 防止重复投影。
7. 现有 Event Outlook 静态日历回归不受影响。
```

### 3.6 Event Insight 导入与任务改动

```powershell
uv run python -m pytest tests/test_event_insight_jobs.py tests/test_event_insight_import_api.py tests/test_event_outlook_timeline.py -q
```

覆盖点：

```text
1. create_job 使用 idempotency_key 避免重复任务。
2. claim_next_job 设置 running、lease_owner、lease_expires_at 和 attempt 日志。
3. 未过期租约不可重复领取，过期租约可恢复领取。
4. fail_job 在次数未耗尽时重新排队，达到上限后标记 failed。
5. text/url/file 三种导入返回 202 + jobId。
6. URL 导入不抓取远端正文。
7. 文件导入拒绝路径穿越，并复制到受控相对目录。
8. 新增 Event Insight API 不影响 Event Outlook 静态日历。
```

### 3.7 Event Insight 事件工作台改动

```powershell
uv run python -m pytest tests/test_event_insight_api.py tests/test_event_insight_repository.py tests/test_event_outlook_timeline.py -q
cmd /c npm --prefix frontend run test -- src/features/event-insight/__tests__/event-list-workspace.test.tsx src/features/event-outlook/__tests__/event-outlook-page.test.tsx --run
```

覆盖点：

```text
1. 事件列表支持关键字、状态、主题、分页和排序基础参数。
2. 事件详情返回主题归属与证据链。
3. 人工编辑写入 event_field_override，不覆盖原始事实。
4. 忽略事件会从默认列表移除，并记录操作日志。
5. 主题创建、事件关联主题和批量操作返回稳定契约。
6. 批量操作采用部分成功，不因单条失败吞掉成功项。
7. 前端事件列表从真实 Event Insight API 加载，覆盖 loading、empty、选择详情。
8. Event Insight 与 Event Outlook 静态日历接口隔离。
```

### 3.8 LLM Runtime 与 Settings 改动

```powershell
uv run python -m pytest tests/test_llm_task_router.py tests/test_llm_settings_api.py tests/test_event_outlook_timeline.py -q
cmd /c npm --prefix frontend run test -- src/features/settings/__tests__/settings-page.test.tsx --run
```

覆盖点：

```text
1. API Key 加密入库，SQLite 中不出现明文。
2. provider 列表和保存响应只返回 apiKeyConfigured/apiKeyPreview。
3. LlmTaskRouter 按 task_type 调用配置的 provider 和模型参数。
4. 被任务映射引用的 provider 禁用返回 409 provider_in_use。
5. Settings 页面从真实 API 加载 provider 与任务映射。
6. Settings 页面保存新 provider 后不展示明文密钥。
7. ArkResearchProvider 保持 Event Outlook 静态日历契约不变。
```

### 3.9 Event Insight 抽取与证据链改动

```powershell
uv run python -m pytest tests/test_event_extraction_service.py tests/test_event_insight_jobs.py tests/test_event_insight_api.py -q
cmd /c npm --prefix frontend run test -- src/features/event-insight/__tests__/event-list-workspace.test.tsx --run
```

覆盖点：

```text
1. LlmTaskRouter 返回的 JSON 会被校验后写入 event/evidence/entity。
2. evidence.excerpt 必须能在原始材料中定位 startOffset/endOffset。
3. extract_event 本地任务可领取、成功完成并标记 succeeded。
4. 模型输出非 JSON 或证据不存在时进入失败路径。
5. 前端详情展示证据来源位置和关联实体。
```

### 3.10 前端改动

在 `frontend/` 目录执行：

```powershell
cmd /c npm run test -- src/app/__tests__/router-shell.test.tsx --run
cmd /c npm run test -- src/features/macro-data/__tests__/macro-page.test.tsx --run
cmd /c npm run test -- src/features/push/__tests__/push-page.test.tsx src/features/push/__tests__/push-preview-panel.test.tsx --run
cmd /c npm run build
```

## 4. 发布前检查（Release Checklist）

1. 后端关键回归通过（至少 3.1 + 涉及域门禁）
2. 前端构建通过（`npm run build`）
3. 健康检查通过：`GET /healthz`
4. 核心接口抽查：
   - `/api/frontend/modules/macro-data?tab=gdp`
   - `/api/frontend/modules/macro-data?tab=employment`
   - `/api/frontend/modules/macro-data/charts/nominal_gdp?range=1y`
   - `/api/frontend/modules/macro-data/charts/nominal_gdp?range=30y`
   - `/api/frontend/modules/macro-data/charts/nominal_gdp?range=1y&frequency=yearly`
   - `/api/frontend/modules/macro-data/charts/unemployment_insurance_fund_expense?range=30y&frequency=yearly`
   - 失业保险基金支出累计值默认种子应覆盖 2005-2024 年 20 个年度点，状态为 `live`
   - `uv run python main.py macro-sync` 后检查 `.data/macro_data.db` 中 `macro_nominal_gdp`、`macro_real_gdp`、`macro_nominal_gdp_growth`、`macro_real_gdp_growth` 的同步状态为 `live`
   - GDP 年度与季度一致性：同一年四个 `quarterly` 点位之和应等于对应 `yearly` 点位；事实表主键应为 `(period_end, frequency)`
   - `POST /api/frontend/modules/market-data/sync/wti_crude_oil` 仅刷新 WTI，不应被布伦特上游失败拖累
   - 全球期货历史解析使用收盘列；东方财富异常时布伦特、黄金、白银、铜可回退新浪外盘日线
   - `/api/frontend/modules/push`
   - `POST /api/push/preview` 使用 `refresh_data=false` 时按所选 `market_chart_range` 从本地历史重绘
   - `POST /api/push/market-chart-refresh` 按当前范围拉取并保留 SQLite 中更早历史
5. 推送链路抽查（本地或测试环境）：
   - 更新配置
   - 预览
   - 手动触发

## 5. 失败处理策略

- 如果是外部数据源波动导致：
  - 优先确认 fallback/sample 是否正常
  - 不直接放行“硬失败”
- 如果是接口字段变更导致前端失败：
  - 先恢复兼容字段
  - 再分阶段迁移前端
- 如果是定时推送失败：
  - 检查 `.data/logs/push_center/` 与 `recent_runs`
  - 优先保证 preview 可用，再恢复真实发送

## 6. Live 测试说明

部分测试依赖外部网络或上游服务，需显式开启环境变量，例如：

```powershell
$env:RUN_LIVE_NEWSNOW_ALL_SOURCES='1'
uv run python -m pytest tests/test_task04_newsnow_integration.py -k NewsNowAllSourcesLiveMatrixTests -q
```

建议：CI 默认只跑稳定回归集，Live 测试作为手动或夜间任务。

## 7. 文档与测试联动要求

以下变更必须同步更新测试与文档：

- 新增/删除 API 字段
- 新增模块或路由
- 新增或调整 SQLite 表结构、seed 数据或本地持久化路径
- 调整 push 配置结构
- 调整 `news_mode` 或刷新语义

需同步更新：

- `docs/api-contract.md`
- `docs/architecture.md`
- `CHANGELOG.md`
- 对应 `tests/` 与 `frontend/src/**/__tests__/`
