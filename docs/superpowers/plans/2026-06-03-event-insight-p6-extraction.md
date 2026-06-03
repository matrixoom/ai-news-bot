# Event Insight P6 Extraction Implementation Plan

**Goal:** 将已入库原始材料通过 `LlmTaskRouter` 抽取为可追溯事件、证据和实体。

## Tasks

- [x] 写红灯测试：成功抽取、证据摘录找不到、extract_event job 成功/失败。
- [x] 增加 prompt 与 JSON schema 文件。
- [x] 增加 `EventExtractionService`，验证 JSON、证据原文位置和入库事务。
- [x] 扩展 Repository：analysis_run、event_source、entity/event_entity、llm_call_log。
- [x] 前端事件详情展示证据来源位置和关联实体。
- [x] 更新文档并跑完整门禁。

**Stop condition:** P6 不做相似搜索、自动去重、主题追踪生成或图谱投影。
