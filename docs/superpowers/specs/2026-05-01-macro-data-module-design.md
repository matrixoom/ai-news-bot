# 宏观数据模块设计

## 背景与目标

本次新增一个与 Push Center 平级的 `Macro Data` 模块，用于集中展示关键宏观指标趋势。模块服务于“趋势洞察”系统的数据分析场景，优先保证结构清晰、可扩展、可测试，并与现有前端壳层和导航模式保持一致。

目标指标共 8 个：

- 名义 GDP
- 实际 GDP
- 居民新增贷款
- 企业新增贷款
- 居民杠杆率
- 企业杠杆率
- PPI
- CPI

## 信息架构

`Macro Data` 作为一级导航入口，与 `Push Center` 平级。

`Macro Data` 下建立 4 个子标签页：

- `GDP`
- `信贷`
- `杠杆率`
- `物价`

子标签页与页面内标签使用同一个 `tab` 查询参数同步。默认进入 `GDP`。无效 `tab` 会自动归一到 `GDP`，避免旧链接或错误链接造成空白页。

## 页面结构

页面复用现有 `ModulePageFrame` 外壳，保持标题、描述、更新时间、工具区和主体内容的视觉一致性。

每个子标签页展示同类指标：

- `GDP`: 名义 GDP、实际 GDP
- `信贷`: 居民新增贷款、企业新增贷款
- `杠杆率`: 居民杠杆率、企业杠杆率
- `物价`: PPI、CPI

每个指标一张 ECharts 图表。图表卡片必须包含：

- 图表标题
- 单位
- 图例
- 当前时间范围
- 时间范围切换控件
- 加载、空数据、错误状态

页面风格保持简洁、专业、数据优先。移动端按单列显示图表，桌面端同类图表可双列展示。

## 时间范围

每张图表独立支持以下预设时间范围：

- 近半年
- 近一年
- 近三年
- 近 5 年
- 近 10 年

预设之外支持自定义起止日期。自定义范围以浏览器本地日期输入为准，前端提交标准日期字符串，展示时间继续遵守项目约定：用户可见时间使用浏览器本地时区格式化，优先复用 `frontend/src/shared/utils/format-local-date-time.ts`。

初始默认范围为近一年。切换子标签页不应重置其他图表已选择的时间范围，除非用户刷新页面。

## 数据契约

推荐新增两个前端接口。

`GET /api/frontend/modules/macro-data`

查询参数：

- `tab`: `gdp | credit | leverage | prices`

用于返回模块元数据、子标签页、当前分类下的图表定义和默认时间范围。

响应建议结构：

```json
{
  "module": {
    "id": "macro-data",
    "label": "Macro Data",
    "description": "GDP, credit, leverage, and inflation indicators"
  },
  "generated_at": "2026-05-01T00:00:00Z",
  "tab": "gdp",
  "charts": [
    {
      "id": "nominal_gdp",
      "title": "名义GDP",
      "unit": "亿元",
      "frequency": "quarterly"
    }
  ]
}
```

`GET /api/frontend/modules/macro-data/charts/{chart_id}`

查询参数：

- `range`: `6m | 1y | 3y | 5y | 10y | custom`
- `start_date`: 自定义范围起始日期，格式 `YYYY-MM-DD`
- `end_date`: 自定义范围结束日期，格式 `YYYY-MM-DD`

用于按单张图表拉取数据，使同一子标签页内的两张图可以选择不同时间范围。

响应建议结构：

```json
{
  "id": "nominal_gdp",
  "title": "名义GDP",
  "unit": "亿元",
  "frequency": "quarterly",
  "range": {
    "type": "1y",
    "start_date": "2025-05-01",
    "end_date": "2026-05-01"
  },
  "series": [
    {
      "name": "名义GDP",
      "points": [
        { "date": "2025-03-31", "value": 12345.67 }
      ]
    }
  ]
}
```

后端保持三层结构：

- Controller: 参数校验、错误返回、调用 Service
- Service: 解析时间范围、组织指标分组、按图表组织序列数据、处理业务异常
- Repository: 读取宏观指标数据，不在 Service 中直接操作数据库

若第一版本地缺少真实数据源，可使用 Repository 提供确定性的样例数据作为临时数据源，但接口契约应保持稳定，便于后续替换为真实数据源。

## 前端实现边界

前端建议新增 feature 目录：

- `frontend/src/features/macro-data/api/`
- `frontend/src/features/macro-data/hooks/`
- `frontend/src/features/macro-data/model/`
- `frontend/src/features/macro-data/components/`

关键组件：

- `MacroDataPage`: 页面容器，负责路由参数和页面布局
- `MacroCategoryTabs`: 页面内分类标签
- `MacroChartCard`: 单张图表卡片，负责标题、单位、图例、时间控件和图表容器
- `MacroRangeControl`: 预设范围与自定义日期选择
- `useMacroDataQuery`: 按分类和时间范围获取数据

导航配置更新：

- `frontend/src/shared/config/nav-items.ts` 增加 `Macro Data` 一级入口
- `moduleDirectories` 增加 Macro Data 子标签页
- 折叠态图标使用 Heroicons，不使用字符缩写或临时 SVG

## 错误与边界处理

前端需要处理：

- 接口加载中
- 接口失败并支持重试
- 单个图表空数据
- 自定义日期缺失
- 自定义起始日期晚于结束日期
- 时间范围超出数据可用区间

后端需要快速失败：

- 无效 `tab`
- 无效 `range`
- 自定义范围缺少日期
- 日期格式错误
- 起始日期晚于结束日期

对外错误信息保持友好；日志记录关键上下文，避免输出敏感信息。

## 测试策略

前端测试：

- 路由 `/macro-data` 可访问并默认显示 `GDP`
- 侧栏显示 `Macro Data` 及 4 个子标签页
- 页面内分类标签切换会同步 URL `tab`
- 每张图表显示标题、单位、图例和时间范围控件
- 预设范围可切换到半年、一年、三年、5 年、10 年
- 自定义日期输入校验起止日期
- 加载、错误、空数据状态可见

后端测试：

- `/api/frontend/modules/macro-data` 返回稳定结构
- 4 个分类分别返回对应指标
- 预设范围解析正确
- 自定义范围校验正确
- 无效参数返回统一错误

## 文档影响

实施时至少同步更新：

- `CHANGELOG.md`
- `docs/api-contract.md`
- `docs/test-strategy.md`

若接口或数据源方案发生变化，需同步记录兼容策略。

## 已确认决策

- 选择分类标签页方案，而不是八图总览网格。
- 分类既出现在 `Macro Data` 下的侧栏子标签页，也出现在页面内标签栏。
- 每张图表独立支持预设与自定义时间范围。
- 第一版可先保证结构和契约清晰，真实数据接入可按现有数据源能力落地。
