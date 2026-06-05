# Event Insight 增量交付记录

本文档记录 Event Insight 从前端样稿到可回归数据链路的增量成果物。

## 已交付范围

| 阶段 | 成果物 | 验证入口 |
| --- | --- | --- |
| P1 | 事件列表、主题溯源、关系图与 Settings 前端样稿 | `/event-outlook?tab=events`、`topic-trace`、`event-graph`、`/settings` |
| P2 | 独立 `.data/event_insight.db` SQLite 事实库与 migration | `tests/test_event_insight_repository.py` |
| P3 | 材料导入与本地任务队列 | `POST /api/frontend/modules/event-insight/documents/import` |
| P4 | 事件列表真实 API 与前端工作台 | `GET /api/frontend/modules/event-insight/events` |
| P5 | LLM Runtime 与 Settings 真实配置 | `/api/system/llm/providers`、`/api/system/llm/task-configs` |
| P6 | 事件抽取与可追溯证据链 | `src/services/event_extraction_service.py` |
| P7 | 中文 n-gram 检索、重复候选和规则聚类 | `src/services/event_retrieval_service.py` |
| P8 | 主题溯源真实 API 与页面 | `GET /api/frontend/modules/event-insight/topics/{topicId}/trace` |
| P9 | 事件关系图 SQLite 投影与页面 | `GET /api/frontend/modules/event-insight/graph` |
| P10 | 主题选择硬化和最终回归 | `GET /api/frontend/modules/event-insight/topics` |

## 发布前回归命令

```powershell
uv run python -m pytest -q
cmd /c npm --prefix frontend run test -- --run
cmd /c npm --prefix frontend run build
```

## 当前边界

1. Event Insight 是已发生事实事件洞察，不复用 Outlook 未来静态日历。
2. SQLite 是事实主库；Neo4j 仍是后续可重建投影。
3. P10 不自动生成主题、不自动确认重复事件、不自动生成关系边。
4. 前端主题溯源和关系图需要先存在主题；没有主题时展示空状态。
5. npm audit 中的依赖安全升级未纳入本轮，以免引入非功能性破坏变更。
