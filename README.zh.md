# AI News Bot

## Python 虚拟环境约定

本仓库统一使用 `uv` 管理项目根目录下的虚拟环境。

- Python 版本：`3.12`
- 虚拟环境目录：`.venv`
- 依赖来源：`pyproject.toml`
- 锁文件：`uv.lock`

重要约定：

- 日常运行请优先使用 `uv run ...`，它会自动选中项目自己的 `.venv`
- 如果需要直接调用解释器，在 Windows 上使用 `.venv\Scripts\python.exe`
- 不要默认系统里的 `python` 就是本项目环境
- 如果解释器用错了，常见现象是误报缺少 `fastapi`、`feedparser`、`pytest` 等包

环境自检：

```powershell
uv run python --version
uv run python -c "import sys; print(sys.executable)"
```

如果需要重新同步环境：

```powershell
uv sync --python 3.12
```

如果 `.venv` 已存在，但包不完整，请把依赖装进这个虚拟环境本身，而不是系统 Python：

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

本项目提供两类运行能力：

- 一个前后端分离的 FastAPI Web 应用
- 一个用于自动推送的 `push` 任务

## 项目结构

### 前端

- 静态前端目录：`src/app/web/static/`
- 主要模块：
  - 热点新闻
  - 宏观趋势
  - 市场模型
  - 事件展望
  - 数据状态
- 入口：`/`

### 后端

- FastAPI 应用：`src/app/web/fastapi_app.py`
- 前端聚合接口：`/api/frontend/dashboard`
- 兼容旧结构接口：`/api/dashboard`
- 兼容旧页面：`/legacy`
- 健康检查：`/healthz`

## 前端工作区

新的 SPA 前端位于 `frontend/`，技术栈为 `Vite + React + TypeScript`。

安装前端依赖：

```powershell
cmd /c npm --prefix frontend install
```

启动前端开发服务器：

```powershell
cmd /c npm --prefix frontend run dev
```

构建供 FastAPI 托管的前端产物：

```powershell
cmd /c npm --prefix frontend run build
```

当 `frontend/dist/index.html` 存在时，`http://127.0.0.1:8000/` 会重定向到 `/dashboard`，并由 FastAPI 为工作台路由提供编译后的 SPA。迁移期间，旧版服务端页面仍保留在 `/legacy`。

## 运行模式

命令入口是 `main.py`：

- `web`：启动 FastAPI Web 服务
- `push`：执行推送任务

## 快速开始

### 1. Python 版本

- 建议使用：`Python 3.12.x`

### 2. 安装 Python 依赖

```powershell
uv python install 3.12
uv sync --python 3.12
```

如果在 Windows 上遇到 `uv` 缓存权限问题，可以改用项目内缓存目录：

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv sync --python 3.12
```

### 3. 初始化 NewsNow submodule

`.third_part_newsnow` 作为第三方上游项目处理，目标是：

- 以 git submodule 方式维护
- 日常开发尽量不改它的源码
- 需要跟进上游时，再显式拉取最新代码

初始化当前仓库固定的 submodule 提交，并安装其依赖：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/init-newsnow-submodule.ps1
```

如果你要把 submodule 更新到 upstream 最新提交：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/init-newsnow-submodule.ps1 -UpdateRemote
```

如果你只想初始化 submodule，不执行 `npm install`：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/init-newsnow-submodule.ps1 -SkipInstall
```

### 4. 启动 Web 服务

```powershell
uv run python main.py web --host 127.0.0.1 --port 8000
```

`web` 模式现在默认开启热加载，`src/` 下后端 Python 代码修改后会自动重启服务。

如果你想关闭热加载：

```powershell
uv run python main.py web --host 127.0.0.1 --port 8000 --no-reload
```

浏览器访问：

- `http://127.0.0.1:8000/`

### 5. 执行 push 任务

```powershell
uv run python main.py push
```

## 推送中心说明

- 推送中心相关文件都在 `.data/` 目录下：
  - `.data/push_center.json`：当前可编辑配置
  - `.data/push_center.state.json`：调度器运行状态
  - `.data/push_center.template.json`：生成出来的模板配置快照
- 当前默认的市场日报时间是 `Asia/Shanghai` 时区下的 `08:00`、`12:05`、`17:00`。
- 中午档位特意改成了 `12:05`，而不是 `12:00` 或 `11:45`，这样港股上午盘已经收盘，恒生科技这类指数才能按“推送前最近一次已收盘价”生成。
- 每次推送都会用 `force_refresh=True` 重新构建 dashboard snapshot，所以推送应该拿的是“推送前最新可用数据”，而不是旧的 dashboard 缓存。
- 市场模块现在按“最近一次已收盘会话”取值：
  - A 股宽基指数在 `11:30` 和 `15:00` 之后分别可以取上午收盘和全天收盘
  - 港股指数（如 `HSTECH`）在 `12:00` 和 `16:15` 之后分别可以取上午收盘和全天收盘
- 推送日志会写到：
  - `.data/logs/push_center/manual/YYYY-MM/YYYY-MM-DD.jsonl`
  - `.data/logs/push_center/scheduled/YYYY-MM/YYYY-MM-DD.jsonl`
- 推送中心页面也会显示最近执行记录，页面看到的历史和磁盘日志应该一致。

## 完整本地运行流程

### 1. 初始化 Python 依赖

```powershell
uv python install 3.12
uv sync --python 3.12
```

### 2. 初始化 NewsNow submodule

```powershell
powershell -ExecutionPolicy Bypass -File scripts/init-newsnow-submodule.ps1
```

### 3. 启动主项目 Web 服务

```powershell
uv run python main.py web --host 127.0.0.1 --port 8000
```

该命令默认就是后端热加载模式，开发时不需要手动反复重启。

### 4. 打开前端页面

```text
http://127.0.0.1:8000/
```

前端加载约束：

- 首页 shell 不能被慢模块阻塞。
- `news`、`macro`、`market`、`events`、`status` 都是在首屏渲染后异步补齐。
- `push` 模块必须保持按需加载，只在用户进入推送中心时再请求，因为它要生成完整预览，明显比其他模块更重。
- 后续前端改动需要保持这条约束，不要把 `push` 恢复成首页预加载。

### 5. 按需切换新闻模式

- `hybrid`：`http://127.0.0.1:8000/?news_mode=hybrid`
- `api`：`http://127.0.0.1:8000/?news_mode=api`
- `upstream`：`http://127.0.0.1:8000/?news_mode=upstream`

## 新闻数据模式

仪表盘支持三种新闻数据模式：

- `hybrid`：优先走 NewsNow 聚合 API，失败时回退到 upstream 原始抓取
- `api`：只使用 NewsNow 聚合 API
- `upstream`：直接使用本地 NewsNow upstream 项目抓取

前端页面支持通过查询参数指定模式：

```text
http://127.0.0.1:8000/?news_mode=upstream
```

可选值：

- `hybrid`
- `api`
- `upstream`

## Upstream 服务启动

当页面使用 `upstream` 模式时，主项目会尝试自动拉起本地 NewsNow 开发服务。

如果你需要手动调试 upstream 服务，使用：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-newsnow-upstream.ps1
```

停止它可以使用：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-newsnow-upstream.ps1
```

默认地址：

- `http://127.0.0.1:5173`

可选环境变量：

- `NEWSNOW_UPSTREAM_PROJECT_DIR`
- `NEWSNOW_UPSTREAM_BASE_URL`

## 运行状态检查

### 查看主项目状态

```powershell
Invoke-WebRequest http://127.0.0.1:8000/healthz -UseBasicParsing
```

### 查看 upstream 服务状态

```powershell
Invoke-WebRequest http://127.0.0.1:5173/healthz -UseBasicParsing
```

### 查看 `8000` 端口是否在监听

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

### 查看 `5173` 端口是否在监听

```powershell
Get-NetTCPConnection -LocalPort 5173 -State Listen
```

### 查看是谁占用了 upstream 端口

```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 5173 -State Listen).OwningProcess
```

如果你改过主项目端口或 upstream 端口，把这里的 `8000`、`5173` 替换成实际端口。

## 停止命令

### 停止主项目

如果当前就在前台终端运行，直接按 `Ctrl + C`。

如果它在后台占用 `8000` 端口运行：

```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess -Force
```

### 停止 upstream NewsNow dev server

如果当前就在前台终端运行，直接按 `Ctrl + C`。

如果它在后台占用 `5173` 端口运行：

```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 5173 -State Listen).OwningProcess -Force
```

或者直接使用辅助脚本：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-newsnow-upstream.ps1
```

### 同时停止两个服务

```powershell
$main = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($main) { Stop-Process -Id $main.OwningProcess -Force }
$upstream = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($upstream) { Stop-Process -Id $upstream.OwningProcess -Force }
```

## 保持 Submodule 干净

如果运行 `.third_part_newsnow` 后产生了生成文件改动，可执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/clean-newsnow-submodule.ps1
```

这个脚本只用于清理第三方 submodule 中常见的生成文件差异，减少无意义改动。

如果 NewsNow 的 dev server 仍在运行，像 `src/routeTree.gen.ts` 这类生成文件可能会被立即重新写回。先停止 upstream 开发服务，再执行清理脚本。

## API 路由

| 路径                      | 方法 | 说明 |
| ------------------------- | ---- | ---- |
| `/`                       | GET  | 前端页面入口 |
| `/api/frontend/dashboard` | GET  | 前端聚合数据接口 |
| `/api/dashboard`          | GET  | 旧版结构化接口 |
| `/legacy`                 | GET  | 旧版服务端页面 |
| `/healthz`                | GET  | 健康检查 |

## 数据模式说明

`web` 模式下默认使用 `prefer_live_data=True`：

- 优先尝试实时数据源
- 如果实时数据链路失败，则回退到样例数据
- 保证页面可访问，不因单个数据源失败导致整体不可用

## 测试

执行主回归测试集：

```powershell
uv run python -m pytest tests/test_task03_web_app_shell.py tests/test_task04_news_pipeline.py tests/test_live_provider_fallbacks.py tests/test_task04_newsnow_integration.py -q
```

执行 NewsNow 全量源 live 验证：

```powershell
$env:RUN_LIVE_NEWSNOW_ALL_SOURCES='1'
uv run python -m pytest tests/test_task04_newsnow_integration.py -k NewsNowAllSourcesLiveMatrixTests -q
```

## 关键文件

- `main.py`
- `src/app/web/fastapi_app.py`
- `src/app/web/frontend_payload.py`
- `src/app/web/static/index.html`
- `src/app/web/static/styles.css`
- `src/app/web/static/app.js`
- `src/providers/newsnow_provider.py`
- `scripts/init-newsnow-submodule.ps1`
- `scripts/start-newsnow-upstream.ps1`
- `scripts/stop-newsnow-upstream.ps1`
- `scripts/clean-newsnow-submodule.ps1`
