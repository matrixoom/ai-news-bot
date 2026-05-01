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
- push center 配置、预览、触发逻辑
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
- Macro Data 分类子标签、图表卡片和自定义时间范围
- push 页面行为（保存配置、预览、触发）

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
uv run python -m pytest tests/test_task05_macro_monitoring.py tests/test_task06_market_models.py tests/test_task07_events_outlook.py -q
```

### 3.4 Push 相关改动

```powershell
uv run python -m pytest tests/test_task08_push_workflow.py tests/test_push_center_module.py tests/test_email_notifier.py -q
```

### 3.5 前端改动

在 `frontend/` 目录执行：

```powershell
cmd /c npm run test -- src/app/__tests__/router-shell.test.tsx --run
cmd /c npm run test -- src/features/macro-data/__tests__/macro-page.test.tsx --run
cmd /c npm run build
```

## 4. 发布前检查（Release Checklist）

1. 后端关键回归通过（至少 3.1 + 涉及域门禁）
2. 前端构建通过（`npm run build`）
3. 健康检查通过：`GET /healthz`
4. 核心接口抽查：
   - `/api/frontend/modules/macro-data?tab=gdp`
   - `/api/frontend/modules/macro-data/charts/nominal_gdp?range=1y`
   - `/api/frontend/modules/push`
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
