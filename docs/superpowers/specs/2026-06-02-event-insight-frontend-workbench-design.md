# Event Insight Frontend Workbench Design

## 1. Design Goal

在不改变现有 `Event Outlook` 国内 / 国际未来事件日历行为的前提下，新增一组面向研究材料分析的高密度工作台页面。

本轮前端先以确定性的 Mock 数据交付可浏览效果，为后续 API、SQLite、任务队列和大模型能力提供稳定的页面契约。

## 2. Navigation

现有 `Event Outlook` 默认入口继续指向国内静态日历：

```text
Event Outlook
  ├── 国内
  ├── 国际
  ├── 事件列表
  ├── 主题溯源
  └── 事件关系图

Settings
  └── 大模型配置
```

路由约定：

```text
/event-outlook?tab=domestic
/event-outlook?tab=international
/event-outlook?tab=events
/event-outlook?tab=topic-trace
/event-outlook?tab=event-graph
/settings
```

`domestic` 与 `international` 才能调用现有静态日历接口。三个新增事件洞察 Tab 不得把自身值传给静态日历查询。

## 3. Visual Direction

页面沿用当前 SPA 的浅色研究工作台风格：

```text
页面背景：slate-100
主要表面：white
边框：slate-200
正文：slate-700 / slate-950
主操作：blue-600
状态：green / amber / rose / violet 的低饱和浅底标签
圆角：6px - 8px
阴影：低对比度轻阴影
图标：仅使用 Heroicons
```

页面采用桌面优先设计。窄屏下允许表格和关系图横向滚动，筛选器换行；不得为了移动端压缩而牺牲研究信息密度。

## 4. Page Specifications

### 4.1 Event List

事件列表页集中查看从材料中提取的结构化事件。页面由标题操作区、筛选工具栏、事件表格和详情抽屉组成。

事件表格展示：事件标题、材料与证据数量、类型、可信度、主题、发生时间、状态。

详情抽屉展示：摘要、主题、本地时区时间、关联实体、分析任务、关键证据、完整证据链入口。

### 4.2 Topic Trace

主题溯源页按主题还原事件演进路径。页面由主题选择、四张摘要指标卡、阶段条、垂直事件时间线和当前阶段判断组成。

当前阶段必须有明显选中态。时间线事件按时间倒序展示，每条包含标题、时间和摘要。

### 4.3 Event Graph

事件关系图用于查看因果、并行、风险与跟随关系。页面采用关系过滤、图谱画布、节点详情三栏布局。

第一阶段只交付静态可读画布，不引入图谱依赖。后续接入 ECharts 或经技术验证后的图谱库。

### 4.4 LLM Settings

大模型配置页用于管理事件抽取、聚类、主题摘要和关系判断所用模型。页面采用模型服务列表、当前模型配置表单和任务默认模型映射表。

第一阶段仅展示 Mock 表单，不保存密钥。真实配置、脱敏、加密、连接测试与任务映射在统一 LLM Runtime 增量中实现。

## 5. State Ownership

```text
URL state:
  event-outlook tab

Local component state:
  mock list selected event
  graph selected node
  filter form values

Server state:
  第一阶段无新增 server state
  后续使用 TanStack Query 接入 /api/frontend/modules/event-insight/*
```

## 6. Incremental Delivery

| Increment | Visible Artifact | Verification |
| --- | --- | --- |
| I1 | 四个 Mock 工作台页面、导航与静态日历兼容 | 打开六个路由；前端测试；生产构建 |
| I2 | 独立 SQLite 事实库与迁移 | `.data/event_insight.db`；repository 测试 |
| I3 | 材料导入与可恢复任务 | 导入接口返回 `202 + jobId`；任务状态可查询 |
| I4 | 事件列表接入真实 API | 列表筛选、详情、编辑、批量操作可验证 |
| I5 | 统一 LLM 配置 | 配置脱敏、连接测试、任务映射可验证 |
| I6 | 抽取与证据链 | 固定材料可生成可回溯事件证据 |
| I7 | 检索、去重与主题聚类 | FTS、候选去重、人工确认可验证 |
| I8 | 主题溯源接入真实 API | 主题演进线与待验证线索可验证 |
| I9 | 关系图接入真实图谱 | 节点、边、降级提示与路径查询可验证 |
| I10 | 端到端收口 | 固定材料全链路回归与发布门禁 |

## 7. Approved Mockup

浏览器审核稿：

```text
docs/mockups/event-insight-frontend-workbench.html
```

该文件用于视觉对照，不作为生产 UI 代码。
