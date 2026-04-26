# Macro 房价研判模块设计

## 1. 需求理解

本次变更围绕 `Macro` 模块新增一个独立标签页：

- 新增 Macro 一级标签页 **房价研判**，内部 key 使用 `housing_outlook`。
- `Compare` 视图属于历史功能，本设计不再包含删除或精简现有 Macro 标签页的工作；后续如需精简 Macro 旧视图，单独设计和实施。
- 房价研判以可靠历史数据、指标图表和数据变化为中心，预测结论只是对数据变化的批注层，优先级低于数据呈现本身。
- 模块目标是观察房价涨跌趋势和影响因子变化，而不是预测成交、投资或库存本身。

研判范围：

- 全国整体。
- 一线城市：北京、上海、广州、深圳。
- 新一线样本城市：杭州、成都、南京、武汉、重庆、苏州、西安、郑州、天津、长沙。

批注周期：

- 未来 3 个月。
- 未来 1 年。
- 未来 5 年。
- 未来 10 年。
- 长期趋势。

核心宏观因子：

- 名义 GDP 与实际 GDP。
- 企业 PPI。
- 居民新增贷款。
- 居民收入预期。

## 2. 设计目标与非目标

### 2.1 设计目标

- 将房价研判作为 `Macro` 下的独立一级 tab 接入，复用现有数据持久化、服务聚合、前端图表和接口契约模式。
- 所有房价目标、宏观因子、趋势批注、关联分析结果持久化到本地 SQLite。
- 优先展示来源可靠的历史数据、指标更新状态、趋势图表、数据表和因子关联。
- 趋势批注信号作为历史数据和数据变化的解释，不作为页面唯一中心。
- 短周期批注和长周期判断使用不同模型语义，避免把长期结构判断伪装成精确数值预测。
- 保持现有 `/api/frontend/modules/macro` 字段兼容，新增字段只做向后兼容扩展。

### 2.2 非目标

- 第一版不预测具体房价点位或涨跌百分比。
- 第一版不做机器学习黑箱模型训练。
- 第一版不引入远程数据库或外部任务队列。
- 第一版不修改 `.third_part_newsnow/`。
- 第一版不删除、归档或重构 Macro 既有 `Overview`、`Compare`、`Indicators`、`Sources` 标签页。

## 3. 影响分析

### 3.1 后端影响范围

- `src/domain/`：新增房价研判领域模型。
- `src/services/`：新增 SQLite store 与研判 service。
- `src/providers/`：扩展宏观 provider 对房价和收入预期代理指标的抓取或样例 fallback。
- `src/app/web/frontend_payload.py`：在 Macro payload 中追加房价研判区块。
- `src/services/dashboard_service.py`：Macro module 聚合时接入房价研判 service。

### 3.2 前端影响范围

- `frontend/src/pages/macro-page.tsx`：新增 `housing_outlook` 一级 tab，不改变现有 tab 的历史行为。
- `frontend/src/features/macro/model/*`：扩展类型与 adapter，适配房价研判 payload。
- `frontend/src/features/macro/components/*`：新增房价研判组件，保留现有 Macro 组件。
- `frontend/src/features/macro/__tests__/macro-page.test.tsx`：更新页面行为测试。

### 3.3 文档与测试影响

- 更新 `docs/api-contract.md` 的 Macro 模块响应字段。
- 更新 `docs/architecture.md` 的 Macro 模块职责。
- 更新 `CHANGELOG.md` 记录兼容策略。
- 增加后端 store/service/API 测试和前端渲染测试。

## 4. 数据口径

### 4.1 房价目标变量

优先使用国家统计局 70 个大中城市商品住宅销售价格指数。

第一版采集并存储以下口径：

- 新建商品住宅价格指数。
- 二手住宅价格指数。
- 环比变化。
- 同比变化。
- 可取得时保留定基指数。

趋势批注使用新房和二手房的综合结果，默认二手房权重略高，因为二手房更能反映存量市场真实价格压力。图表层必须同时保留新房与二手房原始序列，不能只展示综合结论。

### 4.2 城市组聚合

- `national`：全国整体，第一版使用已纳入城市池的等权聚合；后续可升级为成交权重、人口权重或库存权重。
- `tier1`：北京、上海、广州、深圳等权聚合。
- `new_tier1_sample`：杭州、成都、南京、武汉、重庆、苏州、西安、郑州、天津、长沙等权聚合。
- 单城市：上述 14 个城市各自保留明细信号。

### 4.3 宏观因子

- `gdp_nominal`：名义 GDP 增速。
- `gdp_real`：实际 GDP 增速。
- `gdp_gap`：名义 GDP 增速减实际 GDP 增速，用作价格与经济增长分化代理。
- `ppi`：企业 PPI。
- `household_new_loans`：居民新增贷款。
- `household_income_expectation`：居民收入预期或收入信心代理指标。

收入预期数据优先接入央行城镇储户问卷；若实时解析不稳定，第一版必须提供样例 fallback，并在状态中标记 `sample` 或 `degraded`。

## 5. 数据呈现与趋势批注设计

### 5.1 数据中心原则

房价研判页的主角是数据本身，预测只是批注：

- 默认子 tab 为 **历史数据**，展示全部来源可靠的房价、宏观因子、收入预期和信贷数据。
- 每个指标必须展示最新值、历史走势、更新频率、来源、最近同步时间和数据状态。
- 同一数据会随时间持续追加，图表必须支持时间序列自然增长，不依赖固定样本长度。
- 后续新增因子时，应通过指标注册表和 payload 配置扩展，不要求重写页面结构。
- 趋势批注以标记、说明、因子贡献或图表 annotation 的形式贴在数据旁边，不覆盖原始数据判断。

### 5.2 子 Tab 设计

房价研判 `housing_outlook` 下设子 tab：

- **历史数据**：默认页，展示所有来源可靠的历史数据、数据表和趋势图。
- **因子关联**：展示房价与 GDP、PPI、居民新增贷款、收入预期等因子的相关系数、最佳滞后期和样本量。
- **趋势批注**：展示 3 个月、1 年、5 年、10 年、长期的方向性批注、置信度和解释。
- **数据来源**：展示来源列表、口径说明、同步状态、fallback 状态和最近更新时间。

### 5.3 短周期批注模型

适用周期：

- 未来 3 个月。
- 未来 1 年。

批注输出：

- `direction`：`up | flat | down`。
- `score`：标准化趋势分数，范围建议为 `-100` 到 `100`。
- `confidence`：`low | medium | high`。
- `summary`：中文解释。
- `factor_contributions`：各因子贡献。

基础逻辑：

- 房价动量：最近 3 到 6 个月新房和二手房环比趋势。
- 信贷因子：居民新增贷款改善时加分，收缩时减分。
- 收入预期：收入预期改善时加分，恶化时减分。
- PPI：PPI 修复可作为企业利润和名义需求改善代理，但对居民购房需求权重低于贷款和收入预期。
- GDP 缺口：名义 GDP 强于实际 GDP 时说明价格因素较强；若实际 GDP 走弱同时名义 GDP 走强，需要降低置信度。

分数阈值：

- `score >= 20`：上涨。
- `-20 < score < 20`：震荡。
- `score <= -20`：下跌。

### 5.4 长周期结构批注模型

适用周期：

- 未来 5 年。
- 未来 10 年。
- 长期。

批注输出仍为趋势方向，但语义是结构判断，不是短期量化预测。

第一版结构因子：

- 长期实际收入趋势。
- 居民部门信用扩张能力。
- 房价相对收入压力，第一版可用房价指数与收入预期代理构造简化指标。
- 城市能级差异：一线城市抗跌权重高于新一线样本整体。
- 长期通胀和名义增长环境：用名义 GDP 与实际 GDP 缺口代理。

长期批注必须带风险提示：

- 样本不足时置信度不得为 `high`。
- 长期趋势不得展示为精确涨跌幅。
- 若结构因子互相冲突，方向应偏 `flat`，并降低置信度。

## 6. SQLite 数据库设计

数据库默认路径建议沿用 `.data/`：

- `.data/housing_outlook.db`

### 6.1 `housing_price_history`

用途：存储城市级房价历史。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `city_code` | `TEXT NOT NULL` | 城市编码，使用稳定英文或拼音标识，例如 `beijing`、`hangzhou`。 |
| `city_name` | `TEXT NOT NULL` | 城市中文名称，用于前端展示和人工核对。 |
| `city_group` | `TEXT NOT NULL` | 城市分组，取值包括 `national`、`tier1`、`new_tier1_sample`、`city`。 |
| `property_type` | `TEXT NOT NULL` | 房屋类型，区分 `new_home` 新建商品住宅和 `resale_home` 二手住宅。 |
| `period_end` | `TEXT NOT NULL` | 数据期末日期，使用 ISO 日期格式，月度数据取当月最后一天。 |
| `period_label` | `TEXT NOT NULL` | 展示用周期标签，例如 `2026-03`。 |
| `mom_pct` | `REAL` | 环比涨跌幅，单位为百分比；源数据缺失时允许为空。 |
| `yoy_pct` | `REAL` | 同比涨跌幅，单位为百分比；源数据缺失时允许为空。 |
| `fixed_base_index` | `REAL` | 定基价格指数，可取得时保存；不可取得时为空。 |
| `source_url` | `TEXT NOT NULL` | 数据来源页面或文件地址，用于追踪口径。 |
| `provider_key` | `TEXT NOT NULL` | 数据提供方标识，例如 `official-macro` 或 `sample-macro`。 |
| `released_at` | `TEXT NOT NULL` | 数据发布日期或来源公布日期。 |
| `last_seen_at` | `TEXT NOT NULL` | 本地最后一次同步到该记录的时间。 |

主键：

- `(city_code, property_type, period_end)`

索引：

- `(city_group, property_type, period_end)`
- `(period_end, city_code)`

### 6.2 `housing_macro_factors`

用途：存储研判因子历史。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `factor_code` | `TEXT NOT NULL` | 因子编码，例如 `gdp_nominal`、`gdp_real`、`gdp_gap`、`ppi`、`household_new_loans`。 |
| `period_end` | `TEXT NOT NULL` | 因子所属期末日期，按因子频率取月末、季末或年末。 |
| `period_label` | `TEXT NOT NULL` | 展示用周期标签，例如 `2026-Q1` 或 `2026-03`。 |
| `value` | `REAL NOT NULL` | 因子数值，统一存储为已标准化后的数值。 |
| `unit` | `TEXT NOT NULL` | 因子单位，例如 `%`、`tn yuan`、`index`。 |
| `frequency` | `TEXT NOT NULL` | 发布频率，取值包括 `monthly`、`quarterly`、`yearly`。 |
| `source_url` | `TEXT NOT NULL` | 因子来源页面或文件地址。 |
| `provider_key` | `TEXT NOT NULL` | 数据提供方标识。 |
| `released_at` | `TEXT NOT NULL` | 因子发布日期或来源公布日期。 |
| `last_seen_at` | `TEXT NOT NULL` | 本地最后一次同步到该因子的时间。 |

主键：

- `(factor_code, period_end)`

### 6.3 `housing_trend_annotations`

用途：存储每次趋势批注输出。该表记录对历史数据变化的解释，不代表精确预测点位。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `annotation_id` | `TEXT NOT NULL` | 单次趋势批注 ID，用于关联同一批批注结果、贡献项和相关分析。 |
| `target_scope` | `TEXT NOT NULL` | 研判对象范围，例如 `national`、`tier1`、`new_tier1_sample` 或具体城市编码。 |
| `target_name` | `TEXT NOT NULL` | 研判对象中文名称，例如 `全国整体`、`一线城市`、`杭州`。 |
| `horizon` | `TEXT NOT NULL` | 批注周期，取值包括 `3m`、`1y`、`5y`、`10y`、`long_term`。 |
| `direction` | `TEXT NOT NULL` | 趋势方向，取值为 `up`、`flat`、`down`。 |
| `score` | `REAL NOT NULL` | 标准化趋势分数，建议范围为 `-100` 到 `100`。 |
| `confidence` | `TEXT NOT NULL` | 置信度，取值为 `low`、`medium`、`high`。 |
| `summary` | `TEXT NOT NULL` | 中文趋势批注，说明主要数据变化、驱动因素和风险。 |
| `model_version` | `TEXT NOT NULL` | 模型版本号，例如 `real-estate-trend-v1`。 |
| `generated_at` | `TEXT NOT NULL` | 本次批注生成时间，使用 UTC ISO 时间。 |

主键：

- `(annotation_id, target_scope, horizon)`

### 6.4 `housing_factor_contributions`

用途：存储趋势批注中的因子贡献。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `annotation_id` | `TEXT NOT NULL` | 单次趋势批注 ID，与 `housing_trend_annotations.annotation_id` 对应。 |
| `target_scope` | `TEXT NOT NULL` | 研判对象范围，与趋势批注表保持一致。 |
| `horizon` | `TEXT NOT NULL` | 批注周期，与趋势批注表保持一致。 |
| `factor_code` | `TEXT NOT NULL` | 因子编码，用于关联因子历史和前端图表。 |
| `factor_label` | `TEXT NOT NULL` | 因子中文名称，例如 `居民新增贷款`、`收入预期`。 |
| `contribution` | `REAL NOT NULL` | 因子对趋势分数的贡献值，正数支持上涨，负数支持下跌。 |
| `direction` | `TEXT NOT NULL` | 因子贡献方向，取值为 `positive`、`neutral`、`negative`。 |
| `detail` | `TEXT NOT NULL` | 中文解释，说明该因子为何产生当前贡献。 |

主键：

- `(annotation_id, target_scope, horizon, factor_code)`

### 6.5 `housing_factor_correlations`

用途：存储指标与房价目标的相关分析。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `target_scope` | `TEXT NOT NULL` | 分析对象范围，例如全国、一线城市、新一线样本或具体城市。 |
| `property_type` | `TEXT NOT NULL` | 房价目标类型，区分新房、二手房或综合口径。 |
| `factor_code` | `TEXT NOT NULL` | 被分析的宏观因子编码。 |
| `lag_months` | `INTEGER NOT NULL` | 滞后月数，用于衡量因子领先或滞后房价变化的关系。 |
| `correlation` | `REAL` | 皮尔逊相关系数；样本不足或零方差时允许为空。 |
| `sample_size` | `INTEGER NOT NULL` | 参与计算的有效样本数量。 |
| `window_start` | `TEXT NOT NULL` | 相关分析窗口开始日期。 |
| `window_end` | `TEXT NOT NULL` | 相关分析窗口结束日期。 |
| `computed_at` | `TEXT NOT NULL` | 相关分析计算时间。 |

主键：

- `(target_scope, property_type, factor_code, lag_months, window_end)`

### 6.6 `housing_data_sources`

用途：存储房价研判页使用的数据来源、口径和同步状态，支撑“数据来源”子 tab。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `source_key` | `TEXT NOT NULL` | 数据来源唯一标识，例如 `nbs_70_city_price`、`pbc_household_survey`。 |
| `source_label` | `TEXT NOT NULL` | 数据来源中文名称，例如 `国家统计局 70 城房价`。 |
| `source_url` | `TEXT NOT NULL` | 来源页面或文件地址。 |
| `reliability` | `TEXT NOT NULL` | 来源可靠性，取值为 `official`、`derived`、`sample`。 |
| `coverage` | `TEXT NOT NULL` | 数据覆盖范围说明，例如城市、指标、起止时间。 |
| `frequency` | `TEXT NOT NULL` | 更新频率，例如 `monthly`、`quarterly`。 |
| `status` | `TEXT NOT NULL` | 当前同步状态，取值为 `live`、`degraded`、`sample`、`unavailable`。 |
| `warning_message` | `TEXT NOT NULL` | 同步异常或口径限制说明；正常时为空字符串。 |
| `last_synced_at` | `TEXT NOT NULL` | 最近同步时间。 |

主键：

- `(source_key)`

## 7. 后端接口设计

### 7.1 Macro 模块响应扩展

接口：

- `GET /api/frontend/modules/macro`

新增字段：

```json
{
  "generated_at": "2026-04-25T00:00:00Z",
  "module": {
    "id": "macro",
    "details": []
  },
  "housing_outlook": {
    "status": "live",
    "label": "房价研判",
    "default_sub_tab": "history",
    "sub_tabs": [
      {"value": "history", "label": "历史数据"},
      {"value": "correlations", "label": "因子关联"},
      {"value": "annotations", "label": "趋势批注"},
      {"value": "sources", "label": "数据来源"}
    ],
    "targets": [],
    "factors": [],
    "history_groups": [],
    "annotations": [],
    "correlations": [],
    "sources": []
  }
}
```

兼容策略：

- 不删除既有 `module.details[*].section` 结构。
- 前端 adapter 对 `housing_outlook` 缺失时返回空状态。
- 错误时 Macro 模块整体仍可返回现有对比图；房价研判 tab 单独显示 `unavailable`。
- `housing_outlook.history_groups` 是房价研判的核心数据结构，必须包含可绘图序列、表格行、来源状态和更新频率。
- `housing_outlook.annotations` 是辅助批注结构，不应成为唯一可见内容。

### 7.2 Web 层职责

- Controller 仅处理查询参数、HTTP 状态和错误响应。
- 业务计算放在 service。
- SQLite 读写放在 store。
- Provider 只负责外部源解析和标准化。

## 8. 前端设计

### 8.1 页面结构

`/macro` 页面保留现有历史标签页，并新增一级 tab：

- `房价研判`：新增 tab，内部 key 为 `housing_outlook`。
- `Overview`、`Compare`、`Indicators`、`Sources` 等既有 tab 不在本设计中删除或重构。
- 页面标题仍为 `Macro`，进入 `房价研判` tab 后展示数据中心化的房价研判工作台。
- `房价研判` tab 内默认展示子 tab `历史数据`。

### 8.2 房价研判子 Tab

组件建议：

- `HousingOutlookPanel`
  顶层区块，处理子 tab、empty/loading/error。
- `HousingHistoryDataTab`
  默认子 tab，展示所有可靠历史数据、指标表格和图表，是本模块的核心页面。
- `HousingDataSeriesChart`
  展示房价、新房、二手房、宏观因子和派生指标的时间序列。
- `HousingDataTable`
  展示历史数据明细，支持按城市组、城市、指标、来源状态过滤。
- `HousingCorrelationTab`
  展示因子相关系数、最佳滞后期、样本量和分析窗口。
- `HousingAnnotationTab`
  展示 3 个月、1 年、5 年、10 年、长期的趋势批注、置信度和因子贡献。
- `HousingSourcesTab`
  展示来源、口径、同步状态、fallback 状态和最近更新时间。

交互：

- 一级 Macro tab 选择 `房价研判` 后，进入 `housing_outlook`。
- 房价研判内部子 tab：`历史数据`、`因子关联`、`趋势批注`、`数据来源`。
- 历史数据页默认范围为全国整体，默认指标为新房、二手房综合对比。
- 城市范围选择使用分段控制或下拉：全国、一线、新一线、单城市。
- 指标选择使用复选列表或多选菜单，允许同时展示多个因子。
- 趋势批注页周期选择使用分段控制：3 个月、1 年、5 年、10 年、长期。
- 图表必须支持同一数据随时间持续追加后的自然增长，横轴使用真实周期，不使用固定模拟标签。

### 8.3 历史数据子 Tab 细节

`历史数据` 是房价研判的默认入口，必须优先满足数据阅读和图表分析：

- 顶部显示数据覆盖摘要：指标数量、城市数量、最新周期、官方来源数量、sample/fallback 数量。
- 主图展示新房和二手房价格变化，可切换环比、同比和定基指数。
- 因子图展示 GDP、PPI、居民新增贷款、收入预期等宏观因子的历史走势。
- 数据表展示每条历史记录，列至少包含周期、范围、城市、指标、数值、单位、来源、状态、更新时间。
- 图表上的趋势批注只作为标记或说明出现，例如某周期旁的方向标签、信号强弱或风险提示。
- 若某指标数据缺失，图表保留该指标卡位并展示缺失原因，不用预测结果替代原始数据。

### 8.4 趋势批注呈现原则

趋势批注是辅助层：

- 不在首页面首屏压过历史数据图表。
- 不展示为精确涨跌幅。
- 必须链接到驱动该批注的原始数据和因子贡献。
- 置信度低时必须显式展示原因，例如样本不足、来源降级、因子冲突。

## 9. 错误处理与降级

- Provider 抓取失败时记录 warning 日志，包含 `indicator_code`、`source_url`、错误类型。
- Service 不吞异常；房价研判数据或批注生成失败时返回独立 `unavailable` 状态，不影响现有 Macro pair 对比。
- Store upsert 使用事务，确保同一次刷新不会写入半截模型输出。
- 长期批注样本不足时返回 `confidence=low`。
- 所有对外错误信息保持友好，不泄露敏感路径或原始堆栈。

## 10. 测试策略

### 10.1 后端测试

- Store 测试：
  - 房价历史 upsert 幂等。
  - 因子历史 upsert 幂等。
  - 趋势批注与贡献项在同一事务写入。
- Service 测试：
  - 短期分数阈值：上涨、震荡、下跌。
  - 长期样本不足时降置信度。
  - 相关系数计算处理样本不足和零方差。
- API 测试：
  - `/api/frontend/modules/macro` 包含 `housing_outlook`。
  - `housing_outlook` 缺失或 unavailable 时现有 `module.details` 仍可渲染。

### 10.2 前端测试

- Macro 页面显示 `房价研判` 一级 tab。
- 现有 `Compare` 内容仍显示现有 pair 卡片。
- 房价研判默认进入 `历史数据` 子 tab。
- 历史数据子 tab 显示可靠历史数据表和图表。
- 趋势批注子 tab 显示多个周期的方向批注。
- 空数据时显示房价研判 empty 状态。
- API 缺少 `housing_outlook` 时页面不崩溃。

### 10.3 回归检查清单

1. 原功能验证点：现有宏观 pair 对比卡片、相关分析图、source links 和既有 Macro tabs 仍可用。
2. 新功能验证点：`房价研判` tab、历史数据图表、历史数据表、趋势批注、因子贡献图、关联分析图可渲染。
3. 边界情况：样本不足、单城市缺数据、某因子缺失、长期批注冲突信号。
4. 异常处理：provider 失败、SQLite 写入失败、API 返回 unavailable。
5. 配置兼容性：未开启实时数据时使用 sample fallback；旧 Macro payload 字段保持兼容。

## 11. 风险与后续建议

- 官方页面结构变化会影响实时抓取，因此第一版必须保留 sample fallback 和明确的数据状态。
- 全国整体等权聚合不等同于官方全国房价指数，页面应标注为模型聚合口径。
- 5 年、10 年和长期趋势应持续表达为结构判断，避免输出精确涨跌幅。
- 后续可引入库存、土地成交、人口流入、租金收益率和房价收入比，增强长期模型解释力。
