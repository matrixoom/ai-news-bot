# Task 03 Route Map And ViewModel

## 栈与渲染模式

当前 Web 壳子采用：

- FastAPI 作为主 Web 应用对象
- 服务端渲染 HTML 作为首页
- JSON API 作为后续前端扩展和推送复用的数据出口

这样可以保持：

- Python 代码复用高
- 本地运行简单
- 后续升级为更复杂前端时仍保留稳定的数据契约

## 路由图

### `/`

职责：

- 渲染监控大盘首页
- 展示结构化样例数据
- 提供数据刷新时间和模块状态

### `/healthz`

职责：

- 返回最小健康探针
- 用于本地开发和未来部署探活

### `/api/dashboard`

职责：

- 返回首页所需的完整 Dashboard ViewModel
- 作为后续前端和推送装配的共享数据出口

### `404`

职责：

- 对未知路由返回自定义错误页
- 保持与首页同一视觉语言

## ViewModel 规范

### `dashboard_summary`

- `title`
- `subtitle`
- `as_of_label`
- `coverage_note`
- `highlights`

### `news_sections`

每个 section 包含：

- `key`
- `title`
- `status`
- `description`
- `items`

每个 item 包含：

- `title`
- `source`
- `published_at`
- `tag`

### `macro_sections`

每个指标卡包含：

- `key`
- `label`
- `value`
- `context`
- `status`

### `market_sections`

每个市场卡包含：

- `key`
- `label`
- `close_value`
- `ma20_value`
- `signal`
- `status`

### `event_sections`

每个事件窗口包含：

- `key`
- `title`
- `status`
- `items`

每个 item 包含：

- `title`
- `time_window`
- `confidence`
- `source`

### `data_status`

每个数据状态项包含：

- `key`
- `label`
- `status`
- `detail`

## 状态与数据归属

- 首页只消费 `DashboardService` 的结构化输出
- 页面模板不直接读取 provider 原始结果
- 业务聚合和视图装配在服务层完成
- 渲染层只负责 HTML 或 JSON 输出

## 空态与错误态

- 某个 section 无数据时，页面必须保留模块标题和空态文案
- `/api/dashboard` 异常时返回 `503` JSON
- 首页渲染异常时返回 `503` HTML
- 未知路由统一返回自定义 `404`

## 后续迁移点

- Task 04 开始逐步把示例新闻替换为真实新闻 pipeline 输出
- Task 05 和 Task 06 开始逐步替换宏观与市场示例数据
- Task 08 再把共享 ViewModel 输出接入 push 报告装配
