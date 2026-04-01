# Task 05: Macro Indicators Monitoring

## 状态

Completed for implementation phase.

## 本次已交付产物

- 宏观指标协议文档：[05-indicator-registry-and-display-protocol.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/05-indicator-registry-and-display-protocol.md)
- 宏观领域模型：`src/domain/macro_monitoring.py`
- 宏观监测服务：`src/services/macro_monitoring_service.py`
- Dashboard 集成：`src/services/dashboard_service.py`
- 验收测试：`tests/test_task05_macro_monitoring.py`

## 目标

新增宏观经济指标监测模块，支持后续持续扩展。

## 第一版关注指标

第一版已覆盖：

- CPI
- PPI
- 名义 GDP
- 实际 GDP
- 社会融资
- 居民杠杆率
- 政府杠杆率

“股民存款”暂不进入核心承诺，等后续确认稳定口径后再扩展。

## 设计原则

- 宏观模块围绕“指标定义、来源、频率、最新值、上期值、趋势、发布时间”展开
- 页面不只显示数字，也显示口径和更新时间
- 新增指标应通过注册表扩展，而不是修改核心渲染逻辑

## 本阶段交付

- 宏观指标清单
- 指标注册表设计
- 数据标准化方案
- 页面展示协议

## 验收标准

- 新增一个宏观指标只需配置和 provider 增补，不必改核心页面逻辑
- 每个指标都有来源和更新时间
- 无法取数时页面有降级显示

## 难点

- 指标更新频率差异大
- 某些指标可能没有稳定免费 API，只能走官方页面解析

## 优先级

P1

## 验收结果

- 注册表已覆盖 7 个首批宏观指标
- 宏观服务已支持最新值、上期值、变化标签和趋势判断
- 缺失数据会降级为保留卡片但标记 `unavailable`
- Dashboard 宏观区已经接入注册表驱动的卡片结构

## 下一步

直接进入 [06-market-models-and-daily-dashboard.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/06-market-models-and-daily-dashboard.md)。
