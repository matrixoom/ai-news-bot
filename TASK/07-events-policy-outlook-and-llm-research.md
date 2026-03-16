# Task 07: Events, Policy Outlook And LLM Research

## 状态

Completed for implementation phase.

## 本次已交付产物

- 事件过滤协议：[07-confidence-and-research-protocol.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/07-confidence-and-research-protocol.md)
- 事件领域模型：`src/domain/events_outlook.py`
- 预告服务：`src/services/events_outlook_service.py`
- 验收测试：`tests/test_task07_events_outlook.py`

## 目标

新增未来 1 周 / 1 月 / 3 月 / 6 月的热点会议、政策、政策落地预告模块。

## 验收结果

- 四个固定时间窗口已经固化
- 低可信、无来源记录默认被过滤
- 首页只展示中高可信、可追溯记录
- provider 失效时窗口会降级但不消失

## 下一步

直接进入 [08-push-workflow-and-automation.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/08-push-workflow-and-automation.md)。
