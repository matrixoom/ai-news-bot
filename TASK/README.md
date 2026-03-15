# Project Redesign Task Plan

本目录基于最新的 `TODO/plan.md` 重写，目标不再只是增强“AI 新闻推送脚本”，而是把项目重构为：

- 一个可运行在 GitHub Actions 之外的 Web 主页面
- 一个仍然保留推送能力的自动化报告系统
- 一个围绕财经 / 时政 / 科技资讯、宏观指标、市场模型的可扩展监控平台

## 新的产品目标

第一阶段不是继续堆功能，而是完成产品形态升级：

- 从“单一日报脚本”升级为“Web 主页面 + 推送脚本”
- 从“AI 新闻摘要”升级为“财经时政监控大盘”
- 从“LLM 驱动内容输出”升级为“数据采集、结构化加工、规则分析、LLM 总结协同”

## 新架构原则

- Web 页面是主入口，推送脚本是从属入口
- 数据采集层、分析层、展示层、推送层解耦
- 所有外部数据源都必须有 provider 抽象
- 规划按测试驱动推进，每一阶段都必须可验证
- 优先选免费、开源、可自动化的数据源；不稳定数据源必须有降级策略

## 推荐任务顺序

1. [01-target-architecture-and-migration.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/01-target-architecture-and-migration.md)
2. [02-data-source-feasibility-and-provider-strategy.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/02-data-source-feasibility-and-provider-strategy.md)
3. [03-web-homepage-and-app-shell.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/03-web-homepage-and-app-shell.md)
4. [04-news-intelligence-pipeline.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/04-news-intelligence-pipeline.md)
5. [05-macro-indicators-monitoring.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/05-macro-indicators-monitoring.md)
6. [06-market-models-and-daily-dashboard.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/06-market-models-and-daily-dashboard.md)
7. [07-events-policy-outlook-and-llm-research.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/07-events-policy-outlook-and-llm-research.md)
8. [08-push-workflow-and-automation.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/08-push-workflow-and-automation.md)
9. [09-testing-strategy-and-delivery-gates.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/09-testing-strategy-and-delivery-gates.md)

## 里程碑

- M1: 完成目标架构和目录迁移方案，明确 Web / 数据 / 推送边界
- M2: 完成免费数据源评估和 provider 抽象
- M3: Web 首页跑通，能够展示静态或样例数据
- M4: 新闻、宏观、市场模型三大主模块接通
- M5: 预告模块和推送脚本接入
- M6: 测试、CI、配置文档补齐

## 关键约束

- 不在设计阶段直接假设某个免费数据源长期稳定
- 所有模块都要支持“无数据时降级”
- 每个任务完成后都要能通过测试，再进入下一任务

## 建议优先级

- P0: 架构迁移、数据源策略、测试门禁
- P1: Web 首页、新闻情报管线、市场与宏观模块
- P2: 预告模块、推送编排、体验优化
