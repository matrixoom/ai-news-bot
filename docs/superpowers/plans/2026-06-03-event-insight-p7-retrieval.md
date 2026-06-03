# Event Insight P7 Retrieval/Dedup/Topic Clustering Plan

**Goal:** 增加高质量检索、重复候选和规则主题聚类，不做破坏性自动合并。

- [x] 红灯测试：中文 n-gram 召回、重复候选、聚类主题。
- [x] 增加 sqlite-vec 可选加载器。
- [x] 增加 `EventRetrievalService`。
- [x] 复用 Repository 查询 helpers，避免为 P7 提前扩大数据层接口。
- [x] 更新文档并跑门禁。

**Stop condition:** 不自动确认重复、不删除事件、不生成主题溯源摘要。
