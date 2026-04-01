# Task 03: Web Homepage And App Shell

## 状态

Completed for implementation phase.

## 本次已交付产物

- Web 主入口设计与路由说明：[03-route-map-and-viewmodel.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/03-route-map-and-viewmodel.md)
- 首页最小可运行版本：`src/app/web/app.py`、`src/app/web/fastapi_app.py`
- 本地开发服务入口：`src/app/web/server.py`
- Dashboard ViewModel 示例实现：`src/services/dashboard_service.py`
- 验收测试：`tests/test_task03_web_app_shell.py`

## 目标

新增一个简洁的 Web 主页面，作为项目新的主入口，主题为“财经时政类资讯监控大盘”。

## 页面职责

这个页面不是博客，也不是复杂交易终端。第一版只需要承担：

- 展示当天监控总览
- 展示科技 / 财经 / 时政新闻摘要
- 展示宏观指标面板
- 展示市场模型面板
- 展示未来会议 / 政策预告
- 提供刷新时间和数据状态

## 第一版页面结构

- 顶部总览区
- 三栏新闻区
- 宏观指标区
- 市场模型区
- 事件与政策预告区
- 数据状态与更新时间区

## Web 栈决策

当前阶段采用：

- 服务端渲染 HTML
- JSON API 提供同一份 Dashboard ViewModel
- FastAPI 作为目标 Web 入口
- 保留兼容的轻量 WSGI 包装，避免任务 1 测试和旧代码断裂

## App Shell 路由

- `/`：首页
- `/healthz`：健康检查
- `/api/dashboard`：结构化数据接口
- 404：自定义错误页

## 本阶段交付

- Web 主入口设计
- 首页信息架构
- Dashboard ViewModel 规范
- 页面最小可运行版本

## 验收标准

- 能在本地启动 Web 服务
- 首页能渲染结构化示例数据
- 页面和推送脚本入口职责分离

## 难点

- 需要控制范围，避免过早把任务拖入前端工程化
- 需要让首页和 API 共用同一份结构化快照，而不是拼两套数据

## 优先级

P1

## 验收结果

- 首页已经具备总览、新闻、宏观、市场、事件、数据状态六个区域
- `/api/dashboard` 已返回任务 3 约束的 Dashboard ViewModel
- 404 和服务异常都有独立错误输出
- Web 展示层与推送入口继续通过 `DashboardService` 解耦

## 下一步

直接进入 [04-news-intelligence-pipeline.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/04-news-intelligence-pipeline.md)。
