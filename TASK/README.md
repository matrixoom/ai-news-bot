# AI News Bot Next-Step Development Plan

本目录用于承接 `TODO/plan.md` 中的需求，并结合当前项目现状整理出下一步开发任务。

## 当前判断

现有项目已经具备以下基础能力：

- 通过 RSS 获取 AI 新闻
- 使用 LLM 进行两阶段筛选与总结
- 通过邮件、Webhook、Slack、Telegram、Discord 推送
- 通过 GitHub Actions 定时运行

但也存在明显短板：

- 内容域过窄，目前几乎只覆盖 AI / 科技新闻
- 抓取链路主要依赖 RSS，没有真正接入搜索增强
- 缺少去重、时效过滤、排序和质量控制
- 缺少财经数据模块
- 缺少热点会议 / 政策落地预告模块
- 缺少自动化测试

## 目标拆分

下一阶段建议分 5 个任务流推进：

1. 重构内容采集与报告装配基础层
2. 扩展新闻范围到科技 / 财经 / 时政
3. 新增指数与鱼盆模型数据模块
4. 新增热点会议与政策预告模块
5. 补齐单元测试、集成测试和发布验证

## 推荐执行顺序

1. [01-foundation-and-content-pipeline.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/01-foundation-and-content-pipeline.md)
2. [02-multi-domain-news.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/02-multi-domain-news.md)
3. [03-market-data-and-fishbowl-model.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/03-market-data-and-fishbowl-model.md)
4. [04-events-and-policy-outlook.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/04-events-and-policy-outlook.md)
5. [05-testing-release-and-operations.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/05-testing-release-and-operations.md)

## 里程碑建议

- M1: 完成内容采集基础重构，输出稳定的“当日热点池”
- M2: 完成科技 / 财经 / 时政三类日报
- M3: 完成指数数据表格和鱼盆模型摘要
- M4: 完成未来 1 周 / 1 月 / 3 月 / 6 月预告模块
- M5: 完成测试和 GitHub Actions 验证

## 交付标准

- 每个模块都必须有配置项、日志、失败降级策略
- 报告生成必须可按模块开关控制
- 所有外部 API 调用都必须可 mock，便于测试
- GitHub Actions 需要支持最小可运行配置
