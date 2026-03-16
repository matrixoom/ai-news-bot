# Task 09 Test Matrix And Delivery Gates

## 单元测试

- Task 01: 架构骨架与 Web 基础契约
- Task 02: provider 契约与主备源策略
- Task 04: 新闻去重、当日过滤、三域配置
- Task 05: 宏观注册表、趋势推导、缺数降级
- Task 06: MA20、偏离度、鱼盆状态
- Task 07: 可信度过滤和来源约束
- Task 08: 报告装配和推送渠道隔离

## 集成测试

- FastAPI `/api/dashboard` 返回四大业务模块
- Push report 使用统一 `DashboardSnapshot`
- Push job 在部分 notifier 失败时仍返回成功

## 交付门禁

- Gate 1: 任务 1-2 的接口设计与测试通过
- Gate 2: 任务 3 的首页与 API 测试通过
- Gate 3: 任务 4 的新闻管线测试通过
- Gate 4: 任务 5-6 的宏观和市场测试通过
- Gate 5: 任务 7-8 的事件和推送测试通过
- Final Gate: Task 1-10 全量回归与集成测试通过
