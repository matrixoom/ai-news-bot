# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

## 常用命令

### Python 环境

始终使用 `uv run`，以确保选用项目本地的 `.venv`：

```powershell
uv run python --version          # 应为 3.12.x
uv run python main.py web        # 启动 FastAPI 服务（默认开启热重载）
uv run python main.py push       # 执行一次性推送任务
```

修复或重新同步环境：

```powershell
uv sync --python 3.12
```

### 前端

```powershell
cmd /c npm --prefix frontend install        # 安装依赖
cmd /c npm --prefix frontend run dev        # 启动开发服务器
cmd /c npm --prefix frontend run build      # 生产构建（tsc + vite）
cmd /c npm --prefix frontend run test       # 运行 vitest
```

运行单个前端测试：

```powershell
cmd /c npm --prefix frontend run test -- src/app/__tests__/router-shell.test.tsx --run
```

### 后端测试

运行快速回归门禁：

```powershell
uv run python -m pytest tests/test_task03_web_app_shell.py tests/test_task09_integration_suite.py -q
```

按领域回归测试：

```powershell
# 新闻 / provider 策略
uv run python -m pytest tests/test_task02_provider_strategy.py tests/test_task04_news_pipeline.py tests/test_task04_newsnow_integration.py -q

# 宏观 / 市场 / 事件
uv run python -m pytest tests/test_task05_macro_monitoring.py tests/test_task06_market_models.py tests/test_task07_events_outlook.py -q

# 推送
uv run python -m pytest tests/test_task08_push_workflow.py tests/test_push_center_module.py tests/test_email_notifier.py -q
```

运行单个测试文件：

```powershell
uv run python -m pytest tests/test_task05_macro_monitoring.py -q
```

### 修改后验证

每次代码修改后必须执行：

- **后端修改后**：运行相关测试套件，确保全部通过
- **前端修改后**：运行 `cmd /c npm --prefix frontend run build`（含 tsc -b + vite build），确保无编译错误
- 两项均通过才算修改完成，不要跳过

# 验证后提交
After every complete file edit, check if the test suite passes. If all tests pass, stage all changed files, generate a conventional commit message summarizing the changes: what was changed, why, and which files were affected. If tests fail, analyze the failure output, fix the code, and re-run tests up to 3 times before asking for help.

### NewsNow 子模块(废弃)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/init-newsnow-submodule.ps1       # 初始化 + npm install
powershell -ExecutionPolicy Bypass -File scripts/init-newsnow-submodule.ps1 -UpdateRemote  # 更新至最新上游
powershell -ExecutionPolicy Bypass -File scripts/start-newsnow-upstream.ps1       # 启动上游开发服务器
powershell -ExecutionPolicy Bypass -File scripts/stop-newsnow-upstream.ps1        # 停止
powershell -ExecutionPolicy Bypass -File scripts/clean-newsnow-submodule.ps1      # 清理脏生成文件
```

## 架构

本项目是一个 **仪表盘 + 推送报告** 系统（"Trend Insight"），后端使用 FastAPI，前端使用 React SPA。

### 目录结构

```
main.py                  # CLI 入口：`web` 或 `push` 模式
src/
  app/web/               # FastAPI 路由、SPA 静态资源托管、前端 payload 适配
  services/              # 业务编排（DashboardService、PushCenterService 等）
  domain/                # 数据类、枚举、结构化类型（无业务逻辑）
  providers/             # 外部数据源适配（live、fallback、sample、NewsNow）
  llm_providers/         # LLM 客户端适配（Claude、OpenAI、DeepSeek、Gemini、Grok）
  notifiers/             # 推送渠道（邮件、Slack、Telegram、Discord、Webhook）
  news/                  # RSS/网页搜索抓取 + 摘要生成
  config.py              # 从 config.yaml + .env 加载配置
frontend/
  src/
    app/                 # 应用外壳、providers、路由
    features/            # 功能模块：dashboard、news、macro、market、events、push、settings、status
    pages/               # 页面级组件（薄封装，核心逻辑在 features/ 中）
    shared/              # 配置、hooks、工具库、类型、UI 原语
    layouts/             # 应用外壳布局
```

### 后端分层（严格）

```
Controller (app/web)  ←  Service (services/)  ←  Provider (providers/)
                                   ↕
                              Domain (domain/)
```

- **Controller**：参数校验、返回响应。禁止包含业务逻辑。
- **Service**：编排 provider、构建快照、缓存。
- **Provider**：封装外部数据源（akshare、NewsNow、样本数据），对外暴露统一契约（定义在 `providers/contracts.py`）。
- **Domain**：纯数据类，不依赖 services 或 controllers。

### 前端结构

每个功能模块遵循以下模式：

```
features/<名称>/
  api/           # HTTP 请求（fetch 封装）
  model/         # 类型定义 + adapter，将 API 响应转换为视图模型
  components/    # UI 组件
  hooks/         # React Query hooks + 状态管理
  __tests__/     # Vitest + Testing Library
```

Adapter（`model/*-adapter.ts`）隔离 UI 与后端字段名。当后端响应字段变更时，需同步更新 adapter + types + tests。

### 核心运行时流程

1. **仪表盘页面**：前端调用 `/api/frontend/dashboard` 或各 `/api/frontend/modules/*` 端点 → `DashboardService` 组装各模块快照 → `frontend_payload.py` 映射为前端友好的格式 → adapter → 视图。

2. **推送**：前端调用 `/api/frontend/modules/push` → `PushCenterService` 管理配置/预览/触发 → `PushReportService` 渲染 HTML 报告 → notifiers 执行推送。

3. **冷启动**：模块返回 HTTP 202，附带 `module.loading=true` 和 `refresh_after_ms`；前端自动轮询直至就绪。

4. **数据降级**：每个 provider 返回 `live | degraded | unavailable`。Service 按 live → fallback → sample 依次降级，确保 UI 始终有内容可展示。



### 重要约定

- **子模块**：`.third_part_newsnow/` 是只读 git 子模块。未经明确要求不得修改其源码。
- **懒加载导入**：`src/services/__init__.py` 和 `src/providers/__init__.py` 使用 `__getattr__` 实现懒加载，不要破坏此模式。
- **删除 = 归档**：永远不要直接 `rm` 文件，改为移动到 `to_delete/` 目录。
- **TypeScript 严格模式**：`tsc -b` 必须通过，`vite build` 才可用。
- **图表要求**：每张图表必须包含标题、单位标注和图例。使用 ECharts，通过 shared 组件调用。
- **注释语言**：注释使用中文，保持简洁、不冗余。
- **AGENTS.md**：包含完整规则手册（提交规范、代码边界、变更流程、回归检查清单）。任何非简单修改前应先阅读该文件。

## 前端图表开发

ECharts + React 集成时的关键约束（基于实际调试经验）：

- **禁止对 wheel 事件使用 stopPropagation**：会阻断 ECharts 内部的 dataZoom 处理器，导致缩放功能失效
- **图表容器挂载时机**：使用 `ref callback` 或确保图表 div 已挂载后再绑定事件监听器。避免在 useEffect 中使用空依赖数组绑定监听器到条件渲染的图表容器上——容器可能在 effect 执行时尚未挂载
- **交互验证**：实现任何图表交互后，必须同时验证：① 新功能正常；② ECharts 内置功能（缩放、tooltip、dataZoom）未被破坏；③ 页面级交互（滚动、缩放）未受负面影响
- **数值参数精确实现**：用户指定的坐标轴范围、刻度间隔等数值参数需精确匹配。不确定时先确认，避免因默认值与期望不符而返工
