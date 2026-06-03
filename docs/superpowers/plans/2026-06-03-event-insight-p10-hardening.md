# Event Insight P10 Hardening Plan

**Goal:** 收尾硬化 Event Insight 增量交付，移除前端固定主题 ID 假设，补发布说明并跑总回归。

- [x] 红灯测试：主题列表 API 返回可选择主题。
- [x] 红灯测试：主题溯源和关系图页面使用主题列表中的 ID 请求详情。
- [x] 增加 Repository/Service/Route 主题列表能力。
- [x] 前端新增 topics API/hook，并改造两个页面的主题选择。
- [x] 更新文档和 Changelog，记录 P4-P10 交付状态。
- [x] 跑最终后端、前端、构建总门禁。

**Stop condition:** 不新增自动主题生成，不新增 Neo4j，不处理 npm audit 依赖升级。
