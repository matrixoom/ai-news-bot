# Task 08 Report And Automation Design

## 报告结构

- 标题与生成时间
- 新闻摘要
- 宏观指标表格
- 市场模型表格
- 事件预告
- 数据状态

## 入口关系

- Web：首页与 API 继续通过 `DashboardService`
- Push：通过 `PushReportService` 把 `DashboardSnapshot` 渲染为 markdown
- `main.py`：仍作为兼容入口，但内部只调用新的 push job

## 渠道策略

- Email 使用 `subject`
- 其他 webhook / chat 渠道统一使用 `title`
- 单个渠道失败只记录，不中断其他渠道
