# Event Insight P9 Event Graph Plan

**Goal:** 将事件关系图从 mock 页面升级为 SQLite-backed 关系投影和真实前端画布。

- [x] 红灯测试：Graph API 返回 topic 范围内的事件节点和关系边。
- [x] 红灯测试：前端关系图从 API 加载节点、边和选中详情。
- [x] 扩展 Repository 关系写入和图谱查询 helper。
- [x] 扩展 `EventInsightService` 和路由。
- [x] 替换 `EventGraphWorkspace` mock 数据，补 API/hook/types。
- [x] 更新契约、架构、测试文档和 Changelog。
- [x] 跑后端、前端和构建门禁。

**Stop condition:** P9 不接 Neo4j，不自动生成关系，只展示 SQLite 中已存在的关系投影。
