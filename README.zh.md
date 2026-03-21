# AI News Bot

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

浏览器访问：

- `http://127.0.0.1:8000/`

### 5. 执行 push 任务

```powershell
uv run python main.py push
```

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

### 4. 打开前端页面

```text
http://127.0.0.1:8000/
```

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
