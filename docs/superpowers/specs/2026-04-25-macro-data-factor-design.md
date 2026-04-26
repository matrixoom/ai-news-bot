# Macro 数据因子与数据模型框架设计

文档状态：设计稿，当前优先服务 Macro 数据因子第一阶段实现。

## 1. 需求理解

本次变更围绕 `Macro` 模块重新建立数据驱动的信息架构：

- 先删除现有 Macro 中全部旧标签页和对应前后端逻辑。旧标签页包括 `Overview`、`Compare`、`Indicators`、`Sources`。
- `Compare` 旧实现也一起移除；后续若需要宏观对比能力，单独重新设计和实现。
- 清理后的 Macro 页面保留三个顶层子模块：**数据因子**、**数据源矩阵** 与 **数据模型**。
- 本次第一阶段只重点设计和实现 **数据因子**；**数据模型** 只预留一个标签页入口，不实现房价研判、经济周期等模型逻辑。
- **数据源矩阵** 作为 Macro 下的一级子标签，用于集中展示每个指标的数据来源可用性、接入优先级、可靠性、覆盖范围和验证状态。
- 房价研判不再作为 Macro 下的直接子标签；它是未来构建在数据因子之上的业务模型，应放入 `数据模型` 模块内。
- 第一版专注于可靠数据获取、SQLite 持久化、数据校验、来源追踪、图表呈现和数据表展示。

数据因子覆盖范围：

- 全国整体。
- 一线城市：北京、上海、广州、深圳。
- 新一线样本城市：杭州、成都、南京、武汉、重庆、苏州、西安、郑州、天津、长沙。

第一批核心数据因子：

- 房价历史数据：新建商品住宅、二手住宅、环比、同比、可取得时的定基指数。
- 名义 GDP 与实际 GDP。
- 企业 PPI。
- 居民新增贷款。
- 居民贷款增速。
- 居民活期存款增速。

## 2. 设计目标与非目标

### 2.1 设计目标

- 清理旧 Macro 标签页，建立 `数据因子`、`数据源矩阵` 与 `数据模型` 三个新的顶层子模块。
- 将 `数据因子` 作为第一阶段核心交付，承载房价、GDP、PPI、居民信贷、居民活期存款等历史数据。
- 将 `数据源矩阵` 作为数据接入的管理视图，明确每个指标的官方源、开源备选源、候选源、不可用原因和最近验证时间。
- 每个指标作为 `数据因子` 下的独立子标签或详情页，支持独立查看趋势图、数据表、来源、口径和质量状态。
- 所有因子定义、历史观测值、来源状态、同步状态持久化到本地 SQLite。
- 数据结构要支持后续持续追加历史数据，也支持新增数据因子时低成本扩展。
- 第一版把数据正确性、来源可靠性、可复核性和图表表达作为交付核心，后续再基于稳定数据设计业务模型。
- 保持现有 `/api/frontend/modules/macro` 字段兼容，新增字段只做向后兼容扩展。

### 2.2 非目标

- 第一版不实现房价研判模型、经济周期模型或其他业务模型。
- 第一版不预测具体房价点位、涨跌百分比或方向。
- 第一版不输出趋势批注、方向判断、趋势分数或置信度。
- 第一版不展示 3 个月、1 年、5 年、10 年、长期等预测周期。
- 第一版不做机器学习黑箱模型训练。
- 第一版不做指标关联分析的模型化结论；相关性、领先滞后等分析放入后续 `数据模型` 设计。
- 第一版不引入远程数据库或外部任务队列。
- 第一版不修改 `.third_part_newsnow/`。
- 第一版不重建旧 `Compare` 能力；宏观对比能力后续单独设计。

## 3. 影响分析

### 3.1 后端影响范围

- `src/domain/`：新增或调整 Macro 数据因子领域模型，包括因子定义、观测值、来源矩阵、来源质量状态。
- `src/services/`：新增 SQLite store 与数据因子 service。
- `src/providers/`：扩展宏观 provider 对房价、居民贷款增速、居民活期存款增速等指标的抓取或 sample fallback。
- `src/app/web/frontend_payload.py`：以 `data_factors`、`source_matrix` 与 `data_models` payload 作为 Macro 模块核心响应，并移除只服务旧 `Overview`、`Compare`、`Indicators`、`Sources` 视图的派生逻辑。
- `src/services/dashboard_service.py`：Macro module 聚合时接入数据因子 service。

### 3.2 前端影响范围

- `frontend/src/pages/macro-page.tsx`：删除 `Overview`、`Compare`、`Indicators`、`Sources` 分支，新增 `数据因子`、`数据源矩阵` 与 `数据模型` 子模块。
- `frontend/src/features/macro/model/*`：扩展类型与 adapter，适配 `data_factors`、`source_matrix` 与 `data_models` payload，并移除仅服务旧标签页的派生模型。
- `frontend/src/features/macro/components/*`：新增数据因子组件；不再使用的旧标签页专用组件按项目规则归档到 `to_delete/`。
- `frontend/src/features/macro/__tests__/macro-page.test.tsx`：更新页面行为测试。

### 3.3 文档与测试影响

- 更新 `docs/api-contract.md` 的 Macro 模块响应字段。
- 更新 `docs/architecture.md` 的 Macro 模块职责。
- 更新 `CHANGELOG.md` 记录兼容策略。
- 增加后端 store/service/API 测试和前端渲染测试。

## 4. 信息架构

### 4.1 Macro 顶层结构

`/macro` 页面第一版只保留三个新子模块：

- **数据因子**：默认入口，负责展示所有可持续更新的宏观与房价历史数据。
- **数据源矩阵**：一级子标签，负责展示每个指标的数据来源可用性、可靠性、覆盖范围、接入优先级和最近验证状态。
- **数据模型**：预留入口，暂不实现具体模型，只展示空状态或建设中状态。

旧标签页删除范围：

- `Overview`：删除入口、路由状态、渲染分支、adapter 派生字段和测试断言。
- `Compare`：删除入口、路由状态、渲染分支、pair analytics、relative performance、spread monitor 和测试断言。
- `Indicators`：删除入口、路由状态、渲染分支和旧指标列表页专用结构。
- `Sources`：删除入口、路由状态、渲染分支和旧独立来源页专用结构。

若需要物理移除旧文件，按项目规则先移动到 `to_delete/`，不直接删除。

### 4.2 数据因子内部结构

`数据因子` 是本次核心模块。页面结构建议：

- 一级为数据因子模块。
- 二级为指标子标签页，每个指标一个子标签或详情页。
- 每个指标详情页包含趋势图、历史数据表、来源说明、口径说明、质量状态和最近更新时间。
- 对于房价这类多维指标，指标页内部再提供城市范围、城市、新房/二手房、环比/同比/定基指数等筛选控件。

第一批指标子标签建议：

- `房价数据`：全国、一线城市、新一线样本城市和单城市的新房、二手房价格变化。
- `名义 GDP`：名义 GDP 或名义 GDP 增速。
- `实际 GDP`：实际 GDP 或实际 GDP 增速。
- `GDP 差值`：名义 GDP 增速减实际 GDP 增速，用作价格与经济增长分化代理。
- `企业 PPI`：工业生产者出厂价格指数或同比。
- `居民新增贷款`：住户部门新增贷款。
- `居民贷款增速`：住户贷款余额同比增速。
- `居民活期存款增速`：住户或个人活期存款同比增速；若稳定来源不足，状态标为 `degraded` 或 `unavailable`。

### 4.3 数据源矩阵结构

`数据源矩阵` 是 Macro 下独立于 `数据因子` 的一级子标签。它回答的问题不是“这个指标走势如何”，而是“这个指标应该从哪里取、当前能否稳定取、是否可信、缺什么”。

页面结构建议：

- 顶部汇总卡片：指标总数、官方主源数量、可稳定接入数量、降级来源数量、不可用来源数量、最近验证时间。
- 主表格：一行表示一个“指标 + 数据来源”组合。
- 筛选器：按指标分类、来源类型、可靠性、可用状态、接入优先级、最近验证时间过滤。
- 行详情：展示来源 URL、字段映射、覆盖范围、频率、口径说明、限制说明、fallback 策略和验证记录。
- 操作入口：第一版只展示状态，不做在线编辑；后续可增加“重新验证”“标记为主源”“补充字段映射”等运维动作。

矩阵状态建议：

- `live`：已接入且最近验证通过。
- `degraded`：可接入但存在口径、频率、字段或稳定性问题。
- `candidate`：可作为候选源，尚未完成稳定验证。
- `unavailable`：当前无法稳定获取或缺少可靠公开来源。

第一批矩阵项建议：

| 指标 | 主源 | 备选源 | 初始状态 | 说明 |
| --- | --- | --- | --- | --- |
| 房价数据 | 国家统计局 70 城商品住宅销售价格指数 | AKShare / 东方财富房价接口作为抓取参考 | `candidate` | 官方源最可信，但需要解析月度发布页面；开源源可用于样例和字段对齐。 |
| 名义 GDP | 国家统计局 GDP 数据 | AKShare、DBnomics、世界银行作为参考 | `candidate` | 优先官方季度数据，国际源只用于交叉校验。 |
| 实际 GDP | 国家统计局 GDP 实际增速 | AKShare、DBnomics、世界银行作为参考 | `candidate` | 需明确使用实际增速还是不变价金额。 |
| GDP 差值 | 本地派生计算 | 无 | `candidate` | 由名义 GDP 增速减实际 GDP 增速得到，依赖上游两个指标质量。 |
| 企业 PPI | 国家统计局 PPI 数据 | AKShare PPI 接口 | `candidate` | 官方源优先，AKShare 适合快速验证历史序列。 |
| 居民新增贷款 | 人民银行金融统计数据报告 | 手工样例或后续 Provider | `candidate` | 需解析月度报告中的住户部门贷款新增额。 |
| 居民贷款增速 | 人民银行金融机构贷款投向统计报告 | 手工样例或后续 Provider | `candidate` | 若只有季度口径，数据因子页必须标注频率。 |
| 居民活期存款增速 | 人民银行相关统计口径待确认 | 无稳定备选 | `degraded` | 该指标公开连续序列不稳定，保留矩阵项和表结构，先不硬造数据。 |

### 4.4 数据模型预留结构

`数据模型` 本次只预留标签页，不实现业务模型。预留说明：

- 未来可在此模块下增加 `房价研判模型`、`经济周期模型`、`通胀压力模型` 等。
- 模型必须依赖已沉淀在 `数据因子` 中的稳定历史数据，不直接绕过数据因子层抓取临时数据。
- 本次页面只展示建设中空状态、模型列表占位和依赖数据因子的说明。
- 本次不展示预测周期、趋势判断、趋势批注、评分或置信度。

## 5. 数据因子口径

### 5.1 房价数据

优先使用国家统计局 70 个大中城市商品住宅销售价格指数。

第一版采集并存储以下口径：

- 新建商品住宅价格指数。
- 二手住宅价格指数。
- 环比变化。
- 同比变化。
- 可取得时保留定基指数。

图表层必须同时保留新房与二手房原始序列，不能只展示综合结论。综合口径只用于辅助对比，必须能回溯到城市级、房屋类型级原始数据。

### 5.2 城市组聚合

- `national`：全国整体，第一版使用已纳入城市池的等权聚合；后续可升级为成交权重、人口权重或库存权重。
- `tier1`：北京、上海、广州、深圳等权聚合。
- `new_tier1_sample`：杭州、成都、南京、武汉、重庆、苏州、西安、郑州、天津、长沙等权聚合。
- 单城市：上述 14 个城市各自保留明细信号。

### 5.3 宏观与居民部门因子

- `gdp_nominal`：名义 GDP 增速。
- `gdp_real`：实际 GDP 增速。
- `gdp_gap`：名义 GDP 增速减实际 GDP 增速，用作价格与经济增长分化代理。
- `ppi`：企业 PPI。
- `household_new_loans`：居民新增贷款。
- `household_loan_growth`：居民贷款余额同比增速，衡量居民部门信用扩张能力。
- `household_demand_deposit_growth`：居民活期存款同比增速，衡量居民端流动性和短期可动用资金变化。

居民收入预期不作为第一版核心因子。该数据更偏问卷口径，连续可机读历史数据不稳定；后续若能确认稳定来源，可作为 `optional` 观察因子补充，不参与第一版核心数据看板。

居民部门数据来源优先级：

- 居民新增贷款：优先使用人民银行月度金融统计数据报告中的住户部门贷款新增额。
- 居民贷款增速：优先使用人民银行金融机构贷款投向统计报告中的住户贷款余额同比增速；若月度口径不可得，按季度口径展示并标注频率。
- 居民活期存款增速：优先寻找人民银行金融统计数据中个人活期存款或住户活期存款口径；若全国连续序列不可稳定取得，第一版标记为 `degraded` 或 `sample`，但保留表结构、图表位置和来源说明。

## 6. 数据获取与呈现设计

### 6.1 数据中心原则

数据因子第一版只关注数据本身：

- 默认进入 **数据因子**，展示全部来源可靠的房价、宏观因子、居民贷款和居民活期存款数据。
- 每个指标子标签必须展示最新值、历史走势、更新频率、来源、最近同步时间和数据状态。
- 同一数据会随时间持续追加，图表必须支持时间序列自然增长，不依赖固定样本长度。
- 后续新增因子时，应通过指标注册表和 payload 配置扩展，不要求重写页面结构。
- 所有图表必须能追溯到来源、口径和原始数值；若数据缺失或降级，必须显式展示原因。

### 6.2 指标详情页设计

每个数据因子详情页建议包含：

- 指标摘要：最新值、最新周期、单位、频率、数据状态、最近同步时间。
- 趋势图：展示该指标历史变化，图表必须有标题、单位、图例。
- 维度筛选：按指标类型提供城市、城市组、房屋类型、环比/同比/定基指数等筛选。
- 数据表：展示周期、维度、数值、单位、来源、状态、发布时间、本地更新时间。
- 来源与口径：展示官方来源、派生算法、覆盖范围、频率和降级说明。
- 空状态：数据不可用时展示缺失原因，不用预测值或模拟判断替代真实数据。

### 6.3 数据质量规则

- 官方来源优先，派生指标必须保留计算口径。
- 每条序列必须展示数据状态：`live`、`degraded`、`sample`、`unavailable`。
- 派生增速必须能回溯到余额或原始公布值；若只能取得增速而无法取得余额，需要在来源说明中标注。
- 不同频率数据允许共存，图表必须标注月度、季度或年度频率，避免误读。
- 第一版不输出方向判断、趋势批注或模型解释；最多展示最新值、同比、环比、样本区间和缺失说明。

## 7. SQLite 数据库设计

数据库默认路径建议沿用 `.data/`：

- `.data/macro_data_factors.db`

### 7.1 `macro_factor_definitions`

用途：存储数据因子定义，支撑前端子标签、单位、频率、来源和扩展能力。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `factor_code` | `TEXT NOT NULL` | 因子编码，例如 `housing_price`、`gdp_nominal`、`ppi`。 |
| `factor_label` | `TEXT NOT NULL` | 因子中文名称，例如 `房价数据`、`名义 GDP`。 |
| `category` | `TEXT NOT NULL` | 因子分类，例如 `housing`、`growth`、`price`、`credit`、`deposit`。 |
| `description` | `TEXT NOT NULL` | 因子用途和口径说明，用于前端详情页展示。 |
| `default_unit` | `TEXT NOT NULL` | 默认展示单位，例如 `%`、`亿元`、`index`。 |
| `frequency` | `TEXT NOT NULL` | 默认发布频率，取值包括 `monthly`、`quarterly`、`yearly`、`mixed`。 |
| `source_key` | `TEXT NOT NULL` | 默认数据来源标识，关联 `macro_data_sources.source_key`。 |
| `storage_table` | `TEXT NOT NULL` | 因子历史数据所在事实表，例如 `macro_housing_price_history`、`macro_gdp_history`。 |
| `calculation_method` | `TEXT NOT NULL` | 派生算法说明；原始指标填 `official_raw`。 |
| `display_order` | `INTEGER NOT NULL` | 前端子标签排序值，数值越小越靠前。 |
| `status` | `TEXT NOT NULL` | 因子当前状态，取值为 `live`、`degraded`、`sample`、`unavailable`。 |
| `created_at` | `TEXT NOT NULL` | 本地创建时间。 |
| `updated_at` | `TEXT NOT NULL` | 本地更新时间。 |

主键：

- `(factor_code)`

索引：

- `(category, display_order)`
- `(status, display_order)`

### 7.2 分表原则

数据因子的定义、展示顺序和来源状态统一放在 `macro_factor_definitions` 与 `macro_data_sources` 中；历史事实数据按数据类型分表存储。

分表原因：

- 不同数据的天然维度不同。房价有城市、城市组、新房/二手房、环比/同比；GDP 有名义/实际/差值和季度频率；PPI 与居民贷款又是另一套口径。
- 分表能让字段含义更清晰，避免大量对某类指标无意义的空字段。
- 分表便于后续独立扩展，例如房价增加面积段、GDP 增加现价/不变价金额、居民贷款增加短贷/中长贷。
- Service 层负责把不同事实表聚合为前端统一的 `data_factors` payload，前端不直接感知数据库分表。

### 7.3 `macro_housing_price_history`

用途：存储城市级房价历史数据。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `city_code` | `TEXT NOT NULL` | 城市编码，使用稳定英文或拼音标识，例如 `beijing`、`hangzhou`。 |
| `city_name` | `TEXT NOT NULL` | 城市中文名称，用于前端展示和人工核对。 |
| `city_group` | `TEXT NOT NULL` | 城市分组，取值包括 `national`、`tier1`、`new_tier1_sample`、`city`。 |
| `property_type` | `TEXT NOT NULL` | 房屋类型，区分 `new_home` 新建商品住宅和 `resale_home` 二手住宅。 |
| `measure` | `TEXT NOT NULL` | 度量口径，取值包括 `mom_pct`、`yoy_pct`、`fixed_base_index`。 |
| `period_end` | `TEXT NOT NULL` | 数据期末日期，使用 ISO 日期格式，月度数据取当月最后一天。 |
| `period_label` | `TEXT NOT NULL` | 展示用周期标签，例如 `2026-03`。 |
| `value` | `REAL NOT NULL` | 房价指标数值，按 `measure` 解释含义。 |
| `unit` | `TEXT NOT NULL` | 数值单位，例如 `%`、`index`。 |
| `source_key` | `TEXT NOT NULL` | 数据来源标识，关联 `macro_data_sources.source_key`。 |
| `source_url` | `TEXT NOT NULL` | 来源页面或文件地址。 |
| `provider_key` | `TEXT NOT NULL` | 数据提供方标识，例如 `official-macro` 或 `sample-macro`。 |
| `quality_status` | `TEXT NOT NULL` | 当前记录质量状态，取值为 `live`、`degraded`、`sample`、`unavailable`。 |
| `quality_message` | `TEXT NOT NULL` | 数据缺失、降级或口径限制说明；正常时为空字符串。 |
| `released_at` | `TEXT NOT NULL` | 数据发布日期或来源公布日期。 |
| `last_seen_at` | `TEXT NOT NULL` | 本地最后一次同步到该记录的时间。 |

主键：

- `(city_code, property_type, measure, period_end)`

索引：

- `(city_group, property_type, measure, period_end)`
- `(period_end, city_code)`
- `(quality_status, period_end)`

### 7.4 `macro_gdp_history`

用途：存储名义 GDP、实际 GDP 和 GDP 差值历史数据。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `gdp_metric` | `TEXT NOT NULL` | GDP 指标类型，取值包括 `nominal_growth`、`real_growth`、`growth_gap`。 |
| `period_end` | `TEXT NOT NULL` | 数据期末日期，季度数据取季末日期。 |
| `period_label` | `TEXT NOT NULL` | 展示用周期标签，例如 `2026-Q1`。 |
| `value` | `REAL NOT NULL` | GDP 指标数值。 |
| `unit` | `TEXT NOT NULL` | 数值单位，例如 `%`。 |
| `frequency` | `TEXT NOT NULL` | 发布频率，通常为 `quarterly` 或 `yearly`。 |
| `source_key` | `TEXT NOT NULL` | 数据来源标识，关联 `macro_data_sources.source_key`。 |
| `source_url` | `TEXT NOT NULL` | 来源页面或文件地址。 |
| `provider_key` | `TEXT NOT NULL` | 数据提供方标识。 |
| `quality_status` | `TEXT NOT NULL` | 当前记录质量状态，取值为 `live`、`degraded`、`sample`、`unavailable`。 |
| `quality_message` | `TEXT NOT NULL` | 数据缺失、降级或口径限制说明；正常时为空字符串。 |
| `released_at` | `TEXT NOT NULL` | 数据发布日期或来源公布日期。 |
| `last_seen_at` | `TEXT NOT NULL` | 本地最后一次同步到该记录的时间。 |

主键：

- `(gdp_metric, period_end)`

索引：

- `(period_end)`
- `(quality_status, period_end)`

### 7.5 `macro_ppi_history`

用途：存储企业 PPI 历史数据。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `ppi_metric` | `TEXT NOT NULL` | PPI 指标类型，例如 `producer_price_yoy`、`producer_price_mom`。 |
| `period_end` | `TEXT NOT NULL` | 数据期末日期，月度数据取当月最后一天。 |
| `period_label` | `TEXT NOT NULL` | 展示用周期标签，例如 `2026-03`。 |
| `value` | `REAL NOT NULL` | PPI 指标数值。 |
| `unit` | `TEXT NOT NULL` | 数值单位，例如 `%` 或 `index`。 |
| `frequency` | `TEXT NOT NULL` | 发布频率，通常为 `monthly`。 |
| `source_key` | `TEXT NOT NULL` | 数据来源标识，关联 `macro_data_sources.source_key`。 |
| `source_url` | `TEXT NOT NULL` | 来源页面或文件地址。 |
| `provider_key` | `TEXT NOT NULL` | 数据提供方标识。 |
| `quality_status` | `TEXT NOT NULL` | 当前记录质量状态，取值为 `live`、`degraded`、`sample`、`unavailable`。 |
| `quality_message` | `TEXT NOT NULL` | 数据缺失、降级或口径限制说明；正常时为空字符串。 |
| `released_at` | `TEXT NOT NULL` | 数据发布日期或来源公布日期。 |
| `last_seen_at` | `TEXT NOT NULL` | 本地最后一次同步到该记录的时间。 |

主键：

- `(ppi_metric, period_end)`

索引：

- `(period_end)`
- `(quality_status, period_end)`

### 7.6 `macro_household_credit_history`

用途：存储居民新增贷款和居民贷款增速历史数据。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `credit_metric` | `TEXT NOT NULL` | 居民信贷指标类型，取值包括 `new_loans`、`loan_balance_growth`。 |
| `period_end` | `TEXT NOT NULL` | 数据期末日期，按来源频率取月末或季末。 |
| `period_label` | `TEXT NOT NULL` | 展示用周期标签，例如 `2026-03`、`2026-Q1`。 |
| `value` | `REAL NOT NULL` | 居民信贷指标数值。 |
| `unit` | `TEXT NOT NULL` | 数值单位，例如 `亿元`、`%`。 |
| `frequency` | `TEXT NOT NULL` | 发布频率，取值包括 `monthly`、`quarterly`。 |
| `source_key` | `TEXT NOT NULL` | 数据来源标识，关联 `macro_data_sources.source_key`。 |
| `source_url` | `TEXT NOT NULL` | 来源页面或文件地址。 |
| `provider_key` | `TEXT NOT NULL` | 数据提供方标识。 |
| `quality_status` | `TEXT NOT NULL` | 当前记录质量状态，取值为 `live`、`degraded`、`sample`、`unavailable`。 |
| `quality_message` | `TEXT NOT NULL` | 数据缺失、降级或口径限制说明；正常时为空字符串。 |
| `released_at` | `TEXT NOT NULL` | 数据发布日期或来源公布日期。 |
| `last_seen_at` | `TEXT NOT NULL` | 本地最后一次同步到该记录的时间。 |

主键：

- `(credit_metric, period_end)`

索引：

- `(credit_metric, frequency, period_end)`
- `(quality_status, period_end)`

### 7.7 `macro_household_deposit_history`

用途：存储居民活期存款增速历史数据。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `deposit_metric` | `TEXT NOT NULL` | 居民存款指标类型，第一版为 `demand_deposit_growth`。 |
| `period_end` | `TEXT NOT NULL` | 数据期末日期，按来源频率取月末或季末。 |
| `period_label` | `TEXT NOT NULL` | 展示用周期标签，例如 `2026-03`、`2026-Q1`。 |
| `value` | `REAL NOT NULL` | 居民存款指标数值。 |
| `unit` | `TEXT NOT NULL` | 数值单位，例如 `%`。 |
| `frequency` | `TEXT NOT NULL` | 发布频率，取值包括 `monthly`、`quarterly`。 |
| `source_key` | `TEXT NOT NULL` | 数据来源标识，关联 `macro_data_sources.source_key`。 |
| `source_url` | `TEXT NOT NULL` | 来源页面或文件地址。 |
| `provider_key` | `TEXT NOT NULL` | 数据提供方标识。 |
| `quality_status` | `TEXT NOT NULL` | 当前记录质量状态，取值为 `live`、`degraded`、`sample`、`unavailable`。 |
| `quality_message` | `TEXT NOT NULL` | 数据缺失、降级或口径限制说明；正常时为空字符串。 |
| `released_at` | `TEXT NOT NULL` | 数据发布日期或来源公布日期。 |
| `last_seen_at` | `TEXT NOT NULL` | 本地最后一次同步到该记录的时间。 |

主键：

- `(deposit_metric, period_end)`

索引：

- `(deposit_metric, frequency, period_end)`
- `(quality_status, period_end)`

### 7.8 `macro_data_sources`

用途：存储数据来源、口径和同步状态，支撑每个指标详情页的来源说明。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `source_key` | `TEXT NOT NULL` | 数据来源唯一标识，例如 `nbs_70_city_price`、`pbc_financial_statistics`。 |
| `source_label` | `TEXT NOT NULL` | 数据来源中文名称，例如 `国家统计局 70 城房价`。 |
| `source_url` | `TEXT NOT NULL` | 来源页面或文件地址。 |
| `provider_key` | `TEXT NOT NULL` | Provider 标识，用于定位抓取或解析逻辑。 |
| `reliability` | `TEXT NOT NULL` | 来源可靠性，取值为 `official`、`derived`、`sample`。 |
| `coverage` | `TEXT NOT NULL` | 数据覆盖范围说明，例如城市、指标、起止时间。 |
| `frequency` | `TEXT NOT NULL` | 更新频率，例如 `monthly`、`quarterly`。 |
| `status` | `TEXT NOT NULL` | 当前同步状态，取值为 `live`、`degraded`、`sample`、`unavailable`。 |
| `warning_message` | `TEXT NOT NULL` | 同步异常或口径限制说明；正常时为空字符串。 |
| `last_synced_at` | `TEXT NOT NULL` | 最近同步时间。 |

主键：

- `(source_key)`

### 7.9 `macro_source_availability_matrix`

用途：存储“指标 + 数据来源”的可用性矩阵，支撑 Macro 下的 `数据源矩阵` 一级子标签。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `matrix_id` | `TEXT NOT NULL` | 矩阵记录唯一标识，建议由 `factor_code`、`source_key` 和 `source_role` 拼接生成。 |
| `factor_code` | `TEXT NOT NULL` | 因子编码，关联 `macro_factor_definitions.factor_code`。 |
| `factor_label` | `TEXT NOT NULL` | 因子中文名称，用于矩阵表格直接展示。 |
| `source_key` | `TEXT NOT NULL` | 数据来源标识，关联 `macro_data_sources.source_key`。 |
| `source_label` | `TEXT NOT NULL` | 数据来源中文名称，例如 `国家统计局 70 城房价`。 |
| `source_role` | `TEXT NOT NULL` | 来源角色，取值为 `primary` 主源、`fallback` 备选源、`reference` 交叉校验源、`manual_sample` 手工样例源。 |
| `source_type` | `TEXT NOT NULL` | 来源类型，取值为 `official`、`open_source`、`commercial`、`manual`、`derived`。 |
| `availability_status` | `TEXT NOT NULL` | 可用状态，取值为 `live`、`degraded`、`candidate`、`unavailable`。 |
| `reliability_level` | `TEXT NOT NULL` | 可靠性等级，取值为 `official`、`derived`、`community`、`sample`。 |
| `coverage_scope` | `TEXT NOT NULL` | 覆盖范围说明，例如全国、70 城、一线城市、季度 GDP、月度 PPI。 |
| `coverage_start` | `TEXT NOT NULL` | 可用数据起始周期；未知时为空字符串。 |
| `coverage_end` | `TEXT NOT NULL` | 可用数据结束周期；持续更新时为空字符串。 |
| `frequency` | `TEXT NOT NULL` | 数据频率，例如 `monthly`、`quarterly`、`yearly`。 |
| `access_method` | `TEXT NOT NULL` | 获取方式，例如 `official_page_parse`、`akshare_api`、`manual_seed`、`derived_calculation`。 |
| `field_mapping_status` | `TEXT NOT NULL` | 字段映射状态，取值为 `ready`、`partial`、`pending`、`blocked`。 |
| `parser_status` | `TEXT NOT NULL` | 解析器状态，取值为 `ready`、`partial`、`pending`、`failed`、`not_needed`。 |
| `license_note` | `TEXT NOT NULL` | 数据许可、引用或使用限制说明；未知时写明待确认。 |
| `priority_order` | `INTEGER NOT NULL` | 同一指标下的来源优先级，数值越小越优先。 |
| `warning_message` | `TEXT NOT NULL` | 降级、不可用或口径限制说明；正常时为空字符串。 |
| `last_verified_at` | `TEXT NOT NULL` | 最近一次人工或自动验证时间。 |
| `created_at` | `TEXT NOT NULL` | 本地创建时间。 |
| `updated_at` | `TEXT NOT NULL` | 本地更新时间。 |

主键：

- `(matrix_id)`

唯一约束：

- `(factor_code, source_key, source_role)`

索引：

- `(factor_code, priority_order)`
- `(availability_status, reliability_level)`
- `(source_role, priority_order)`
- `(last_verified_at)`

### 7.10 `macro_factor_sync_runs`

用途：记录每次数据同步结果，便于定位数据是否正确、是否更新、是否失败。

字段：

| 字段 | 类型 | 中文说明 |
| --- | --- | --- |
| `run_id` | `TEXT NOT NULL` | 同步任务唯一标识。 |
| `source_key` | `TEXT NOT NULL` | 本次同步的数据来源标识。 |
| `factor_code` | `TEXT NOT NULL` | 本次同步的因子编码；全量同步时可填 `all`。 |
| `started_at` | `TEXT NOT NULL` | 同步开始时间。 |
| `finished_at` | `TEXT NOT NULL` | 同步结束时间；未结束时为空字符串。 |
| `status` | `TEXT NOT NULL` | 同步结果，取值为 `success`、`partial`、`failed`。 |
| `inserted_count` | `INTEGER NOT NULL` | 本次新增记录数量。 |
| `updated_count` | `INTEGER NOT NULL` | 本次更新记录数量。 |
| `error_message` | `TEXT NOT NULL` | 失败或部分失败原因；成功时为空字符串。 |

主键：

- `(run_id)`

索引：

- `(source_key, started_at)`
- `(factor_code, started_at)`

## 8. 后端接口设计

### 8.1 Macro 模块响应扩展

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
  "data_factors": {
    "status": "live",
    "label": "数据因子",
    "default_factor_code": "housing_price",
    "groups": [
      {"value": "housing", "label": "房价数据"},
      {"value": "growth", "label": "经济增长"},
      {"value": "price", "label": "价格指标"},
      {"value": "credit", "label": "居民信用"},
      {"value": "deposit", "label": "居民存款"}
    ],
    "factors": [],
    "series": [],
    "table_rows": [],
    "sources": []
  },
  "source_matrix": {
    "status": "candidate",
    "label": "数据源矩阵",
    "summary": {
      "factor_count": 0,
      "source_count": 0,
      "official_primary_count": 0,
      "degraded_count": 0,
      "unavailable_count": 0,
      "last_verified_at": ""
    },
    "rows": []
  },
  "data_models": {
    "status": "reserved",
    "label": "数据模型",
    "models": []
  }
}
```

兼容策略：

- 删除旧 `module.details[*].section` 对比图结构；第一版 Macro payload 以 `data_factors`、`source_matrix` 与 `data_models` 为核心。
- 删除只服务旧 `Overview`、`Compare`、`Indicators`、`Sources` 标签页的前端 adapter 派生字段；后端 payload 不再额外构造这些旧视图专用结构。
- 前端 adapter 对 `data_factors` 缺失时返回空状态。
- 前端 adapter 对 `source_matrix` 缺失时返回数据源矩阵 empty 状态，不影响数据因子页面加载。
- 错误时 Macro 模块返回数据因子的 `unavailable` 状态和友好错误说明。
- `data_factors.factors` 描述指标定义与展示配置；`series` 与 `table_rows` 由 Service 从各类事实表聚合生成，必须包含可绘图序列、表格行、来源状态和更新频率。
- `source_matrix.rows` 用于数据源矩阵表格，不直接承载历史时间序列。
- `data_models` 第一版只作为预留入口，默认 `status` 为 `reserved`，不返回模型计算结果。
- 第一版不返回 `annotations`、`direction`、`score`、`confidence` 等预测判断字段。

### 8.2 Web 层职责

- Controller 仅处理查询参数、HTTP 状态和错误响应。
- 业务计算放在 service。
- SQLite 读写放在 store。
- Provider 只负责外部源解析和标准化。

## 9. 前端设计

### 9.1 页面结构

`/macro` 页面先清理旧标签页，再建立新结构：

- `数据因子`：默认子模块，内部 key 为 `data_factors`。
- `数据源矩阵`：一级子模块，内部 key 为 `source_matrix`。
- `数据模型`：预留子模块，内部 key 为 `data_models`。
- `Overview`、`Compare`、`Indicators`、`Sources`：删除入口、路由状态、渲染分支、测试断言和仅服务这些标签页的派生逻辑。
- 页面标题仍为 `Macro`，默认进入 `数据因子`。
- `数据源矩阵` 展示指标数据来源的可用性，不展示历史走势图。
- `数据模型` 只展示预留态，不展示房价研判或经济周期模型的实际计算结果。

### 9.2 旧标签页删除规则

删除范围：

- 删除 `Overview`、`Compare`、`Indicators`、`Sources` 的标签配置、URL 标签解析分支和页面渲染分支。
- 删除旧 `Compare` 对比页组件、pair analytics、relative performance、spread monitor、旧 source links 展示和相关测试；如后续需要对比能力，重新设计。
- 删除仅服务 `Indicators` 原始序列页和 `Sources` 独立来源页的组件、类型、adapter 派生字段和测试。
- 后端删除仅为旧标签页准备的派生聚合逻辑，包括旧 pair payload、source links 和 correlation 数据。
- 若需要移除文件，按项目规则先移动到 `to_delete/`，不直接物理删除。

保留范围：

- 保留 `/api/frontend/modules/macro` 作为唯一 Macro 模块接口。
- 保留现有 Macro 数据源和历史库中可复用于数据因子的数据，不保留旧页面展示结构。

### 9.3 数据因子组件结构

组件建议：

- `MacroWorkspace`
  顶层区块，处理 `数据因子`、`数据源矩阵` 与 `数据模型` 的子模块切换。
- `MacroDataFactorsPanel`
  数据因子主面板，处理指标子标签、empty/loading/error。
- `MacroFactorTabs`
  展示每个指标子标签，支持后续通过因子定义动态扩展。
- `MacroFactorDetail`
  单个指标详情，展示摘要、趋势图、数据表和来源说明。
- `MacroFactorSeriesChart`
  展示单因子或同因子多维度历史序列。
- `MacroFactorDataTable`
  展示历史观测值明细，支持按周期、区域、度量、来源状态过滤。
- `MacroFactorSourcePanel`
  展示来源、口径、同步状态、fallback 状态和最近更新时间。
- `MacroSourceMatrixPanel`
  数据源矩阵页，展示来源可用性汇总、筛选器、矩阵表格和行详情。
- `MacroSourceMatrixTable`
  展示指标、主源、备选源、可靠性、覆盖范围、接入状态、字段映射状态、解析器状态和最近验证时间。
- `MacroDataModelsReservedPanel`
  数据模型预留页，展示建设中状态和未来模型入口占位。

交互：

- Macro 默认进入 `数据因子`。
- 数据因子默认进入 `房价数据` 指标子标签。
- 房价数据指标内默认范围为全国整体，默认展示新房和二手房同比。
- 选择 `数据源矩阵` 后，默认展示全部指标来源；用户可按指标分类、来源角色、可用状态和可靠性筛选。
- 点击矩阵行后展示来源详情，包括字段映射、覆盖范围、解析方式、口径限制、fallback 策略和最近验证记录。
- 城市范围选择使用分段控制或下拉：全国、一线、新一线、单城市。
- 指标子标签使用横向 tabs 或左侧列表，便于后续新增因子。
- 单个指标内的度量选择使用分段控制或复选列表，例如环比、同比、定基指数。
- 图表必须支持同一数据随时间持续追加后的自然增长，横轴使用真实周期，不使用固定模拟标签。

### 9.4 数据因子详情页细节

每个数据因子详情页必须优先满足数据阅读和图表分析：

- 顶部显示数据覆盖摘要：最新周期、样本区间、记录数量、官方来源数量、sample/fallback 数量。
- 主图展示当前因子的历史走势；房价数据可切换新房、二手房、环比、同比和定基指数。
- 数据表展示每条历史记录，列至少包含周期、区域、子类型、度量、数值、单位、来源、状态、更新时间。
- 来源区展示官方来源、派生算法、发布频率、最近同步时间和异常说明。
- 图表可展示数据质量标记，例如缺失、sample、degraded、口径变化，不展示涨跌方向判断。
- 若某指标数据缺失，图表保留该指标卡位并展示缺失原因，不用预测结果替代原始数据。

### 9.5 数据源矩阵页细节

`数据源矩阵` 是数据接入前的验收与管理入口：

- 顶部显示矩阵摘要：指标数、来源数、官方主源数、可稳定接入数、降级数、不可用数、最近验证时间。
- 表格列至少包含指标、指标分类、来源名称、来源角色、来源类型、可用状态、可靠性、覆盖范围、频率、获取方式、字段映射状态、解析器状态、优先级、最近验证时间。
- 表格支持按指标分类、来源角色、来源类型、可用状态、可靠性和最近验证时间过滤。
- `degraded` 和 `unavailable` 行必须展示明确原因，不能只显示状态标签。
- 第一版不提供在线编辑能力；矩阵数据通过后端 seed、迁移或配置维护。

### 9.6 数据模型预留页

`数据模型` 页第一版只做预留：

- 页面显示未来可支持的模型方向，例如房价研判模型、经济周期模型、通胀压力模型。
- 页面说明模型需要依赖已沉淀的数据因子。
- 不展示任何模型结果、趋势批注、预测周期、评分或置信度。
- 不放置会让用户误以为已有模型可用的操作按钮。

### 9.7 第一版排除范围

第一版明确不做以下内容：

- 不展示上涨、震荡、下跌等方向判断。
- 不展示 3 个月、1 年、5 年、10 年、长期等预测周期。
- 不展示趋势分数、置信度和因子贡献。
- 不在图表上叠加预测类 annotation。
- 后续若增加分析判断层，必须以已验证的历史数据为输入，并重新补充设计。

## 10. 错误处理与降级

- Provider 抓取失败时记录 warning 日志，包含 `indicator_code`、`source_url`、错误类型。
- Service 不吞异常；数据因子获取、解析或持久化失败时返回独立 `unavailable` 状态，不影响 Macro 页面基础加载和全局模块状态。
- Store upsert 使用事务，确保同一次刷新不会写入半截模型输出。
- 数据样本不足时展示缺失说明、样本数量和来源状态，不生成趋势判断。
- 所有对外错误信息保持友好，不泄露敏感路径或原始堆栈。

## 11. 测试策略

### 11.1 后端测试

- Store 测试：
  - 因子定义 upsert 幂等。
  - 房价历史、GDP、PPI、居民信贷、居民存款各事实表 upsert 幂等。
  - 数据来源状态 upsert 幂等。
  - 数据源矩阵 upsert 幂等，且同一指标下来源优先级可稳定排序。
  - 同步记录写入成功、部分失败和失败状态。
- Service 测试：
  - 官方数据解析后数值、单位、周期和来源字段正确。
  - 样本不足时返回明确缺失说明。
  - 房价多维度数据能写入 `macro_housing_price_history`，并由 Service 聚合为前端统一序列和表格行。
  - 居民活期存款增速不可用时返回 `degraded` 或 `unavailable`，不生成模拟结论。
- API 测试：
  - `/api/frontend/modules/macro` 包含 `data_factors`、`source_matrix` 与 `data_models`。
  - `data_factors` 缺失或 unavailable 时返回数据因子 empty/error 状态，不依赖旧 `module.details`。
  - `source_matrix` 缺失时返回数据源矩阵 empty 状态，不影响数据因子页。
  - `data_models` 返回 reserved 状态，不包含模型预测字段。

### 11.2 前端测试

- Macro 页面不再显示 `Overview`、`Compare`、`Indicators`、`Sources` 标签。
- 访问未知或已删除标签参数时回退到 `数据因子`，不进入空白页面。
- Macro 页面显示 `数据因子`、`数据源矩阵` 与 `数据模型` 子标签。
- 数据因子默认进入 `房价数据` 指标子标签。
- 每个指标详情页显示可靠历史数据表和趋势图。
- 数据源矩阵页显示来源可用性汇总、筛选器和矩阵表格。
- 数据源矩阵中降级或不可用来源显示原因。
- 数据模型页显示预留态，不显示预测判断类结果。
- 页面不显示方向、分数、置信度等预测字段。
- 空数据时显示数据因子 empty 状态。
- API 缺少 `data_factors` 时页面不崩溃。

### 11.3 回归检查清单

1. 原功能验证点：Macro 页面入口、加载态、错误态仍可用。
2. 新功能验证点：`数据因子` 子模块、指标子标签、趋势图、历史数据表、数据来源说明、`数据源矩阵` 表格可渲染。
3. 删除验证点：`Overview`、`Compare`、`Indicators`、`Sources` 不再出现在标签栏、URL 状态、测试 mock 和页面渲染分支中。
4. 边界情况：样本不足、单城市缺数据、某因子缺失、来源降级、口径变化。
5. 异常处理：provider 失败、SQLite 写入失败、API 返回 unavailable。
6. 配置兼容性：未开启实时数据时使用 sample fallback；旧 Macro payload 中仅服务旧标签页的字段不再作为兼容承诺。

## 12. 风险与后续建议

- 官方页面结构变化会影响实时抓取，因此第一版必须保留 sample fallback 和明确的数据状态。
- 全国整体等权聚合不等同于官方全国房价指数，页面应标注为模型聚合口径。
- 第一版不做趋势判断；后续若在 `数据模型` 中增加房价研判，应先验证历史数据覆盖度、口径一致性和回测方式。
- 后续可引入库存、土地成交、人口流入、租金收益率和房价收入比，增强长期模型解释力。
