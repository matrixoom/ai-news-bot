# Task 01 Architecture Decision Record

## Status

Accepted

## Context

当前项目是一个以 `main.py` 为单入口的脚本型应用，主流程直接串联：

- 配置加载
- 新闻抓取
- LLM 生成
- 多渠道推送

该结构适合“定时生成并推送一份日报”，但不适合当前目标：

- Web 页面作为主入口
- 多模块监控面板
- 宏观与市场数据并行接入
- 页面与推送共享结构化数据

## Decision

采用“应用入口层 + 领域层 + 服务层 + Provider 层 + Delivery 层”的分层架构。

### Layer 1: App

职责：

- Web 入口
- CLI 入口
- 定时任务入口

约束：

- 不直接访问第三方 API
- 不直接拼装业务对象

### Layer 2: Domain

职责：

- 实体与值对象
- 规则模型
- 统一枚举

约束：

- 不依赖 Web 框架
- 不依赖 requests、LLM SDK、通知 SDK

### Layer 3: Services

职责：

- 聚合多个 provider 的数据
- 执行业务流程
- 生成 dashboard view model 与 push report model

### Layer 4: Providers

职责：

- 封装 RSS、搜索、AKShare、官方宏观源、LLM、豆包等第三方依赖

### Layer 5: Delivery

职责：

- Web 页面渲染
- 邮件 / Webhook / Slack / Telegram / Discord 输出

## Consequences

收益：

- 页面与推送共享同一份结构化数据
- 后续扩模块不会继续堆到 `main.py`
- 外部数据源可替换

代价：

- 初期会有目录迁移和接口抽象成本
- 某些旧模块需要保留兼容层

## Non-Goals

- 当前阶段不直接实现完整 Web 页面
- 当前阶段不重写全部旧模块
- 当前阶段不引入复杂前端工程
