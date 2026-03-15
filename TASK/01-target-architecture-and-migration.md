# Task 01: Target Architecture And Migration

## 状态

Completed for design phase.

## 本次已交付产物

- 目标架构说明：[01-architecture-decision-record.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/01-architecture-decision-record.md)
- 迁移待办清单：[01-migration-backlog.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/01-migration-backlog.md)
- 新目录骨架：`src/app`、`src/domain`、`src/services`、`src/providers`、`src/delivery`

## 目标

把当前“单入口脚本项目”重构为“Web 主入口 + 推送脚本 + 可复用服务层”的目标架构。

## 当前结构问题

- `main.py` 同时负责配置、编排、生成、通知
- `src/news` 同时承担抓取和生成编排
- `src/notifiers` 与主流程强耦合
- 缺少能同时服务 Web 和 Push 的结构化服务层

## 目标架构

建议分为 5 层：

1. `app` 层
2. `domain` 层
3. `services` 层
4. `providers` 层
5. `delivery` 层

建议职责：

- `app`: Web 入口、CLI 入口、任务入口
- `domain`: 数据模型、规则、值对象
- `services`: 报告生成、聚合、调度、评分
- `providers`: RSS、搜索、AKShare、宏观数据、LLM 等外部依赖
- `delivery`: Web 页面渲染、邮件、Webhook、Slack 等输出

## 旧模块到新架构映射

- `main.py` -> `src/app/jobs` 中的 push job 入口
- `src/news/fetcher.py` -> `src/providers` 中的新闻 provider
- `src/news/generator.py` -> `src/services` 中的报告编排服务 + LLM provider
- `src/llm_providers/*` -> `src/providers` 兼容层
- `src/notifiers/*` -> `src/delivery` 兼容层
- `src/config.py` -> 后续迁移为 settings / config service

## 目录骨架

```text
src/
  app/
    cli/
    jobs/
    web/
  domain/
  services/
  providers/
  delivery/
```

## 关键迁移决策

### 1. Web 成为主入口

当前 `main.py` 不再作为长期主入口，只保留为兼容或 push job 入口。

### 2. 服务层统一产出结构化数据

后续 Web 页面和推送报告都只消费服务层结果，不直接依赖抓取器。

### 3. 旧模块先兼容，后迁移

本阶段不直接重写旧逻辑，只冻结旧逻辑并建立新结构骨架。

## 验收结果

- 已明确 Web 主入口和推送脚本入口边界
- 已明确旧模块到新结构的迁移映射
- 已创建不会影响当前运行的目录骨架
- 已形成下一阶段可直接承接的数据源与 Web 设计前提

## 下一步

直接进入 [02-data-source-feasibility-and-provider-strategy.md](/d:/E/documents/gitspaces/ai-news-bot/TASK/02-data-source-feasibility-and-provider-strategy.md)。
