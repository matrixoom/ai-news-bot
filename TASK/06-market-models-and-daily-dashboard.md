# Task 06: Market Models And Daily Dashboard

## 状态

Completed for implementation phase.

## 本次已交付产物

- 市场模型协议：[06-fishbowl-rules-and-panel-protocol.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/06-fishbowl-rules-and-panel-protocol.md)
- 市场领域模型：`src/domain/market_monitoring.py`
- 市场监测服务：`src/services/market_monitoring_service.py`
- 验收测试：`tests/test_task06_market_models.py`

## 目标

新增简洁的经济 / 股市操盘参考模块，第一版重点覆盖宽基指数、20 日均线、鱼盆模型，并在 Web 页面与推送报告中输出。

## 第一版范围

- 主流宽基指数当日收盘价
- 20 日均线
- 偏离度
- 鱼盆模型状态
- 可选的均线模型状态

## 验收结果

- 6 个跟踪指数已注册
- MA20 和偏离度计算已可复现
- 鱼盆模型规则已固化为状态枚举和解释文案
- 单个指数失败会降级为单卡不可用，不影响整体面板

## 下一步

直接进入 [07-events-policy-outlook-and-llm-research.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/07-events-policy-outlook-and-llm-research.md)。
