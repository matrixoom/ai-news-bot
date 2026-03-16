# Task 04: News Intelligence Pipeline

## 状态

Completed for implementation phase.

## 本次已交付产物

- 新闻管线主文档：[04-domain-config-and-summary-protocol.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/04-domain-config-and-summary-protocol.md)
- 领域模型：`src/domain/news_pipeline.py`
- 新闻聚合服务：`src/services/news_pipeline_service.py`
- 验收测试：`tests/test_task04_news_pipeline.py`

## 目标

建立面向科技 / 财经 / 时政三类内容的新闻采集、去重、时效过滤、搜索增强和摘要管线。

## 为什么需要重做

当前实现只适合单一 AI 新闻场景，存在这些不足：

- 只依赖 RSS
- 搜索逻辑未真正接通
- 没有当日过滤
- 没有去重、排序、质量控制
- 无法支撑多内容域

## 目标能力

- 多内容域采集
- RSS + Search 混合采集
- 当日过滤
- 去重
- 来源打分
- LLM 辅助摘要
- 结构化结果输出给 Web 和推送

## 任务拆解

### 1. 统一新闻数据模型

已补齐：

- 标题
- 域
- 来源
- 链接
- 发布时间
- 抓取时间
- 原始摘要
- 是否当日
- 去重键
- 来源权重

### 2. 领域化配置

已支持：

- `technology`
- `finance`
- `policy`

每个域独立配置：

- 搜索查询模板
- 配额
- 摘要策略
- 官方信源与优先信源规则

### 3. 搜索增强

搜索只负责补齐和交叉印证，不直接替代 RSS。

### 4. 去重与排序规则

当前已经实现：

- 基于标题 / 链接的 dedupe key
- 默认只保留包含“当日记录”的新闻组
- 按信源权重、交叉印证数、摘要完整度排序

### 5. 摘要策略

当前先输出结构化卡片协议，深度报告摘要留给后续报告服务。

## 本阶段交付

- 新闻管线设计
- 域配置方案
- 搜索融合方案
- 新闻摘要输出协议

## 验收标准

- 三个内容域能独立运行
- 非当日新闻默认不进入主面板
- 重复新闻不会重复显示
- 搜索结果和 RSS 结果能稳定融合

## 难点

- 时政新闻更依赖信源选择
- 搜索结果发布时间补齐是关键难点

## 优先级

P1

## 验收结果

- 三域配置已经固化为默认配置
- 搜索结果会和 RSS 结果按 dedupe key 融合
- 无当日记录的新闻组会被整体过滤
- 输出结构已经适合继续喂给 Web 首页和后续推送装配

## 下一步

直接进入 [05-macro-indicators-monitoring.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/05-macro-indicators-monitoring.md)。
