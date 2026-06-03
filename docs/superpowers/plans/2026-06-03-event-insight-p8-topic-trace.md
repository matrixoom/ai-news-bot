# Event Insight P8 Topic Trace Plan

**Goal:** 将主题溯源从 mock 页面升级为可验证的 SQLite/API/前端真实数据链路。

- [x] 红灯测试：主题 trace API 返回主题、指标、阶段和时间线。
- [x] 红灯测试：前端主题溯源页面从 API 加载并展示真实数据。
- [x] 扩展 Repository 主题 trace 查询 helper。
- [x] 扩展 `EventInsightService` 和路由。
- [x] 替换 `TopicTraceWorkspace` mock 数据，补 API/hook/types。
- [x] 更新契约、架构、测试文档和 Changelog。
- [x] 跑后端、前端和构建门禁。

**Stop condition:** P8 只做主题事件追溯，不生成 LLM 主题摘要，不做关系图投影。
