# AI News Bot（最新说明）

当前仓库的核心能力有两块：

- FastAPI Web 应用（前后端分离：静态前端 + JSON API）
- 推送报告任务（push 模式）

## 当前架构

### 前端

- 静态前端目录：`src/app/web/static/`
- 侧边栏 + 独立模块展示：
  - 热点新闻
  - 宏观趋势（近 12 个月折线图）
  - 市场模型
  - 事件展望
  - 数据状态
- 访问入口：`/`

### 后端

- FastAPI 应用：`src/app/web/fastapi_app.py`
- 前端聚合接口：`/api/frontend/dashboard`
- 兼容旧接口：`/api/dashboard`
- 兼容旧页面：`/legacy`
- 健康检查：`/healthz`

## 运行模式

主入口是 `main.py`：

- `web`（默认）：启动 FastAPI 服务
- `push`：运行推送任务

## 本地快速启动

### 1. Python 版本

- 建议使用 `Python 3.12.x`

### 2. 安装依赖

PowerShell：

```powershell
uv python install 3.12
uv sync --python 3.12
```

如果在 Windows 遇到类似
`Failed to initialize cache at C:\Users\...\AppData\Local\uv\cache`
的缓存权限报错，请改用项目内缓存目录：

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv sync --python 3.12
```

### 3. 启动 Web 服务

```powershell
uv run python main.py web --host 127.0.0.1 --port 8000
```

浏览器打开：

- `http://127.0.0.1:8000/`（新前端页面）

### 4. 运行推送任务

```powershell
uv run python main.py push
```

## API 路由

| 路径                      | 方法 | 说明 |
| ------------------------- | ---- | ---- |
| `/`                       | GET  | 新前端入口（静态页面） |
| `/api/frontend/dashboard` | GET  | 前端专用聚合数据接口 |
| `/api/dashboard`          | GET  | 旧版结构化接口 |
| `/legacy`                 | GET  | 旧版服务端渲染页面 |
| `/healthz`                | GET  | 健康检查 |

## 实时数据说明

`web` 模式默认使用 `prefer_live_data=True`，行为是：

- 优先尝试真实数据源
- 若真实数据源不可用（缺密钥、缺依赖、网络失败等），自动回退到样例数据
- 保证页面可访问，不会因为单个数据源失败直接不可用

## 真实接口最小化测试

新增测试文件：

- `tests/test_real_interface_minimal.py`

默认执行（单元级，mock 真实 HTTP 调用）：

```powershell
uv run python -m unittest tests.test_real_interface_minimal
```

可选执行 live smoke（会尝试真实接口链路）：

```powershell
$env:RUN_LIVE_SMOKE='1'
uv run python -m unittest tests.test_real_interface_minimal
```

## 已完成本地验证（2026-03-19）

已实际启动 `main.py web` 并验证：

- `/` 返回 `200`
- `/static/app.js` 返回 `200`
- `/api/frontend/dashboard` 返回 `200`
- `news_sections[0].items` 数量为 `10`
- `/legacy` 返回 `200`

## 关键文件

- `main.py`
- `src/app/web/server.py`
- `src/app/web/fastapi_app.py`
- `src/app/web/frontend_payload.py`
- `src/app/web/static/index.html`
- `src/app/web/static/styles.css`
- `src/app/web/static/app.js`
