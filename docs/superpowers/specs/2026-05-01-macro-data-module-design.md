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
- Repository: 读取本地 SQLite 中的宏观指标数据，不在 Service 中直接操作数据库

若第一版本地缺少真实数据源，可通过迁移或 seed 将确定性的样例数据写入 SQLite 指标表，接口仍从 Repository 读取数据库，避免前后端直接依赖内存 mock。

## SQLite 持久化设计

宏观数据模块必须将 8 个指标持久化到本地 SQLite。默认数据库路径建议为：

- `.data/macro_data.db`

项目已有 `src/services/macro_history_store.py` 使用 `macro_indicator_history` 通用表存储多指标历史；本模块不沿用该通用表作为主存储，因为本次需求明确要求“每一个指标数据一张表”。可复用其连接、事务、初始化和 upsert 风格，但新 Repository 需要面向独立指标表读取。

### 指标事实表

每个指标一张事实表：

- `macro_nominal_gdp`: 名义 GDP
- `macro_real_gdp`: 实际 GDP
- `macro_household_new_loans`: 居民新增贷款
- `macro_corporate_new_loans`: 企业新增贷款
- `macro_household_leverage_ratio`: 居民杠杆率
- `macro_corporate_leverage_ratio`: 企业杠杆率
- `macro_ppi`: PPI
- `macro_cpi`: CPI

各指标表采用同构字段，方便 Repository 用注册表映射表名与图表定义，同时保留后续按单表扩展字段的空间。

字段：

| 字段 | 类型 | 约束 | 中文说明 |
| --- | --- | --- | --- |
| `period_end` | `TEXT` | `PRIMARY KEY` | 数据周期结束日期，格式 `YYYY-MM-DD`。 |
| `period_label` | `TEXT` | `NOT NULL` | 展示用周期标签，例如 `2026Q1`、`2026-03`。 |
| `value` | `REAL` | `NOT NULL` | 指标数值。 |
| `unit` | `TEXT` | `NOT NULL` | 单位，例如 `亿元`、`%`、`指数点`。 |
| `frequency` | `TEXT` | `NOT NULL` | 频率，取值建议为 `monthly`、`quarterly`、`yearly`。 |
| `provider_key` | `TEXT` | `NOT NULL` | 数据来源标识，例如 `nbs`、`pboc`、`manual_seed`。 |
| `source_url` | `TEXT` | `NOT NULL` | 数据来源 URL；本地 seed 可记录来源说明或空字符串。 |
| `released_at` | `TEXT` | `NOT NULL` | 数据发布时间；未知时使用空字符串，不使用假时间。 |
| `last_seen_at` | `TEXT` | `NOT NULL` | 本地最后一次写入或确认时间，UTC ISO 字符串。 |

索引：

- 主键 `period_end` 已覆盖时间范围查询。
- 如后续出现按来源过滤需求，再为单表增加 `(provider_key, period_end)`，第一版不提前添加。

写入规则：

- 每张表以 `period_end` 作为幂等 upsert 键。
- 同一次同步中，单个指标表写入与该指标同步状态更新必须在一个事务内完成。
- 不允许 Service 直接拼接 SQL；Repository 根据受控的指标注册表选择表名，避免用户输入影响表名。

### 指标注册与同步状态表

历史数据本身按指标分表，模块元数据和同步状态可使用共享表。

`macro_data_indicator_registry`

用途：记录前端展示和 Repository 查询所需的指标注册信息。

| 字段 | 类型 | 约束 | 中文说明 |
| --- | --- | --- | --- |
| `indicator_id` | `TEXT` | `PRIMARY KEY` | 指标 ID，例如 `nominal_gdp`。 |
| `table_name` | `TEXT` | `NOT NULL UNIQUE` | 指标事实表名。 |
| `category` | `TEXT` | `NOT NULL` | 分类，取值为 `gdp`、`credit`、`leverage`、`prices`。 |
| `title` | `TEXT` | `NOT NULL` | 中文标题。 |
| `unit` | `TEXT` | `NOT NULL` | 默认单位。 |
| `frequency` | `TEXT` | `NOT NULL` | 默认频率。 |
| `display_order` | `INTEGER` | `NOT NULL` | 分类内展示顺序。 |
| `status` | `TEXT` | `NOT NULL` | `live`、`degraded`、`sample`、`unavailable`。 |
| `created_at` | `TEXT` | `NOT NULL` | 创建时间。 |
| `updated_at` | `TEXT` | `NOT NULL` | 更新时间。 |

索引：

- `(category, display_order)` 用于模块元数据接口快速返回当前子标签页图表定义。
- `(status, display_order)` 用于后续质量状态筛选。

`macro_data_sync_state`

用途：记录每个指标最近一次同步状态，方便页面展示更新时间和异常原因。

| 字段 | 类型 | 约束 | 中文说明 |
| --- | --- | --- | --- |
| `indicator_id` | `TEXT` | `PRIMARY KEY` | 指标 ID。 |
| `provider_key` | `TEXT` | `NOT NULL` | 最近使用的数据来源。 |
| `latest_period_end` | `TEXT` | 可空 | 最新周期。 |
| `earliest_period_end` | `TEXT` | 可空 | 最早周期。 |
| `point_count` | `INTEGER` | `NOT NULL DEFAULT 0` | 当前表内记录数。 |
| `status` | `TEXT` | `NOT NULL` | `success`、`partial`、`failed`、`sample`。 |
| `warning_message` | `TEXT` | `NOT NULL DEFAULT ''` | 降级或失败原因。 |
| `synced_at` | `TEXT` | `NOT NULL` | 同步时间。 |

### 读取路径

Repository 读取流程：

1. 从 `macro_data_indicator_registry` 根据 `tab` 取出当前分类下的指标定义和受控表名。
2. 对单张图表请求，根据 `chart_id` 找到指标定义和表名。
3. 根据预设或自定义时间范围计算 `start_date` 与 `end_date`。
4. 查询对应指标事实表：

```sql
SELECT period_end, period_label, value, unit, frequency, released_at
FROM macro_nominal_gdp
WHERE period_end >= ? AND period_end <= ?
ORDER BY period_end ASC;
```

5. 将查询结果映射为前端 `series.points`，并附带单位、频率、同步状态和数据质量状态。

### 迁移与初始化

第一版初始化应包含：

- 创建 8 张指标事实表。
- 创建 `macro_data_indicator_registry` 与 `macro_data_sync_state`。
- seed 8 个指标注册记录。
- 如真实数据源暂未接入，为每张指标表写入少量确定性样例数据，并将状态标记为 `sample`，页面必须明确展示该状态。

后续如果从已有 `macro_indicator_history` 通用表回填数据，应写单独迁移脚本，将可复用指标按 `indicator_code` 拆分写入对应独立表；迁移必须幂等，且不删除旧库数据。

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
- SQLite 初始化会创建 8 张指标事实表、注册表和同步状态表
- 每张指标事实表以 `period_end` 幂等 upsert，并可按时间范围查询
- 单图表接口只读取对应指标表，不走多指标共表
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
- 8 个指标数据必须持久化到本地 SQLite，且每个指标一张事实表。
- 第一版可先通过 seed 写入确定性样例数据，但接口仍从 SQLite Repository 读取，真实数据接入可按现有数据源能力落地。
