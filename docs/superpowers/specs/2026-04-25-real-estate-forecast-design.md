# Macro 房地产趋势预测模块设计

## 1. 需求理解

本次变更围绕 `Macro` 模块做两类调整：

1. 精简现有 Macro 页面，只保留当前中间的 `Compare` 视图，删除 `Overview`、`Indicators`、`Sources` 三个标签及其前后端无用逻辑。
2. 在 Macro 模块内新增房地产房价趋势预测能力，目标是预测房价涨跌趋势，而不是预测成交、投资或库存本身。

预测范围：

- 全国整体。
- 一线城市：北京、上海、广州、深圳。
- 新一线样本城市：杭州、成都、南京、武汉、重庆、苏州、西安、郑州、天津、长沙。

预测周期：

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

- 将房地产趋势预测接入现有 Macro 模块，复用现有数据持久化、服务聚合、前端图表和接口契约模式。
- 所有房价目标、宏观因子、模型输出、关联分析结果持久化到本地 SQLite。
- 以多图表方式展示各指标变化趋势、预测信号、因子贡献和关联分析。
- 短周期预测和长周期判断使用不同模型语义，避免把长期结构判断伪装成精确数值预测。
- 保持现有 `/api/frontend/modules/macro` 字段兼容，新增字段只做向后兼容扩展。

### 2.2 非目标

- 第一版不预测具体房价点位或涨跌百分比。
- 第一版不做机器学习黑箱模型训练。
- 第一版不引入远程数据库或外部任务队列。
- 第一版不修改 `.third_part_newsnow/`。

## 3. 影响分析

### 3.1 后端影响范围

- `src/domain/`：新增房地产预测领域模型。
- `src/services/`：新增 SQLite store 与预测 service。
- `src/providers/`：扩展宏观 provider 对房价和收入预期代理指标的抓取或样例 fallback。
- `src/app/web/frontend_payload.py`：在 Macro payload 中追加房地产预测区块。
- `src/services/dashboard_service.py`：Macro module 聚合时接入房地产预测 service。

### 3.2 前端影响范围

- `frontend/src/pages/macro-page.tsx`：移除 tab 分支，保留 Compare 主视图。
- `frontend/src/features/macro/model/*`：扩展类型与 adapter，删除不再使用的 tab 类型和原始序列页逻辑。
- `frontend/src/features/macro/components/*`：新增房地产预测组件，归档不再需要的 Indicators/Sources 专用组件。
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

预测主信号使用新房和二手房的综合结果，默认二手房权重略高，因为二手房更能反映存量市场真实价格压力。

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

## 5. 模型设计

### 5.1 短周期模型

适用周期：

- 未来 3 个月。
- 未来 1 年。

模型输出：

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

### 5.2 长周期结构模型

适用周期：

- 未来 5 年。
- 未来 10 年。
- 长期。

模型输出仍为趋势方向，但语义是结构判断，不是短期量化预测。

第一版结构因子：

- 长期实际收入趋势。
- 居民部门信用扩张能力。
- 房价相对收入压力，第一版可用房价指数与收入预期代理构造简化指标。
- 城市能级差异：一线城市抗跌权重高于新一线样本整体。
- 长期通胀和名义增长环境：用名义 GDP 与实际 GDP 缺口代理。

长期输出必须带风险提示：

- 样本不足时置信度不得为 `high`。
- 长期趋势不得展示为精确涨跌幅。
- 若结构因子互相冲突，方向应偏 `flat`，并降低置信度。

## 6. SQLite 数据库设计

数据库默认路径建议沿用 `.data/`：

- `.data/real_estate_forecast.db`

### 6.1 `real_estate_price_history`

用途：存储城市级房价历史。

字段：

- `city_code TEXT NOT NULL`
- `city_name TEXT NOT NULL`
- `city_group TEXT NOT NULL`
- `property_type TEXT NOT NULL`
- `period_end TEXT NOT NULL`
- `period_label TEXT NOT NULL`
- `mom_pct REAL`
- `yoy_pct REAL`
- `fixed_base_index REAL`
- `source_url TEXT NOT NULL`
- `provider_key TEXT NOT NULL`
- `released_at TEXT NOT NULL`
- `last_seen_at TEXT NOT NULL`

主键：

- `(city_code, property_type, period_end)`

索引：

- `(city_group, property_type, period_end)`
- `(period_end, city_code)`

### 6.2 `real_estate_macro_factors`

用途：存储预测因子历史。

字段：

- `factor_code TEXT NOT NULL`
- `period_end TEXT NOT NULL`
- `period_label TEXT NOT NULL`
- `value REAL NOT NULL`
- `unit TEXT NOT NULL`
- `frequency TEXT NOT NULL`
- `source_url TEXT NOT NULL`
- `provider_key TEXT NOT NULL`
- `released_at TEXT NOT NULL`
- `last_seen_at TEXT NOT NULL`

主键：

- `(factor_code, period_end)`

### 6.3 `real_estate_forecast_runs`

用途：存储每次预测输出。

字段：

- `run_id TEXT NOT NULL`
- `target_scope TEXT NOT NULL`
- `target_name TEXT NOT NULL`
- `horizon TEXT NOT NULL`
- `direction TEXT NOT NULL`
- `score REAL NOT NULL`
- `confidence TEXT NOT NULL`
- `summary TEXT NOT NULL`
- `model_version TEXT NOT NULL`
- `generated_at TEXT NOT NULL`

主键：

- `(run_id, target_scope, horizon)`

### 6.4 `real_estate_factor_contributions`

用途：存储模型因子贡献。

字段：

- `run_id TEXT NOT NULL`
- `target_scope TEXT NOT NULL`
- `horizon TEXT NOT NULL`
- `factor_code TEXT NOT NULL`
- `factor_label TEXT NOT NULL`
- `contribution REAL NOT NULL`
- `direction TEXT NOT NULL`
- `detail TEXT NOT NULL`

主键：

- `(run_id, target_scope, horizon, factor_code)`

### 6.5 `real_estate_factor_correlations`

用途：存储指标与房价目标的相关分析。

字段：

- `target_scope TEXT NOT NULL`
- `property_type TEXT NOT NULL`
- `factor_code TEXT NOT NULL`
- `lag_months INTEGER NOT NULL`
- `correlation REAL`
- `sample_size INTEGER NOT NULL`
- `window_start TEXT NOT NULL`
- `window_end TEXT NOT NULL`
- `computed_at TEXT NOT NULL`

主键：

- `(target_scope, property_type, factor_code, lag_months, window_end)`

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
  "real_estate_forecast": {
    "status": "live",
    "model_version": "real-estate-trend-v1",
    "targets": [],
    "factors": [],
    "correlations": [],
    "sources": []
  }
}
```

兼容策略：

- 不删除既有 `module.details[*].section` 结构。
- 前端 adapter 对 `real_estate_forecast` 缺失时返回空状态。
- 错误时 Macro 模块整体仍可返回现有对比图；房地产区块单独显示 `unavailable`。

### 7.2 Web 层职责

- Controller 仅处理查询参数、HTTP 状态和错误响应。
- 业务计算放在 service。
- SQLite 读写放在 store。
- Provider 只负责外部源解析和标准化。

## 8. 前端设计

### 8.1 页面结构

`/macro` 页面只保留 Compare 视图：

- 不再显示 `ModuleTabBar`。
- 页面标题仍为 `Macro`。
- 主区域从上到下：
  1. 房地产趋势预测区块。
  2. 现有宏观指标 pair 对比卡片。

### 8.2 房地产趋势预测区块

组件建议：

- `RealEstateForecastPanel`
  顶层区块，处理 empty/loading/error。
- `RealEstateTrendMatrix`
  趋势矩阵，行是全国、一线、新一线、单城市，列是 3 个月、1 年、5 年、10 年、长期。
- `RealEstatePriceTrendChart`
  展示新房与二手房历史走势。
- `RealEstateFactorContributionChart`
  展示每个周期的因子贡献。
- `RealEstateCorrelationChart`
  展示因子相关系数和最佳滞后期。

交互：

- 城市范围选择使用分段控制或下拉：全国、一线、新一线、单城市。
- 周期选择使用分段控制：3 个月、1 年、5 年、10 年、长期。
- 默认选中全国 + 3 个月。

### 8.3 删除逻辑

需要归档到 `to_delete/` 的候选文件：

- `frontend/src/features/macro/components/macro-pair-series-card.tsx`
- 仅服务于 Indicators 或 Sources 独立标签的专用逻辑。

需要直接编辑的文件：

- `frontend/src/features/macro/model/macro-module.types.ts`
- `frontend/src/features/macro/model/macro-module-adapter.ts`
- `frontend/src/pages/macro-page.tsx`
- `frontend/src/features/macro/__tests__/macro-page.test.tsx`

删除原则：

- 不删除仍被 Compare 卡片复用的 source link 展示。
- 不删除现有 pair correlation、spread、relative performance 图。
- 文件删除按项目规则先移动到 `to_delete/`。

## 9. 错误处理与降级

- Provider 抓取失败时记录 warning 日志，包含 `indicator_code`、`source_url`、错误类型。
- Service 不吞异常；房地产预测失败时返回独立 `unavailable` 区块，不影响现有 Macro pair 对比。
- Store upsert 使用事务，确保同一次刷新不会写入半截模型输出。
- 长期预测样本不足时返回 `confidence=low`。
- 所有对外错误信息保持友好，不泄露敏感路径或原始堆栈。

## 10. 测试策略

### 10.1 后端测试

- Store 测试：
  - 房价历史 upsert 幂等。
  - 因子历史 upsert 幂等。
  - 预测 run 与贡献项在同一事务写入。
- Service 测试：
  - 短期分数阈值：上涨、震荡、下跌。
  - 长期样本不足时降置信度。
  - 相关系数计算处理样本不足和零方差。
- API 测试：
  - `/api/frontend/modules/macro` 包含 `real_estate_forecast`。
  - `real_estate_forecast` 缺失或 unavailable 时现有 `module.details` 仍可渲染。

### 10.2 前端测试

- Macro 页面不再显示 tab bar。
- Compare 内容仍显示现有 pair 卡片。
- 房地产趋势矩阵显示多个周期。
- 空数据时显示房地产预测 empty 状态。
- API 缺少 `real_estate_forecast` 时页面不崩溃。

### 10.3 回归检查清单

1. 原功能验证点：现有宏观 pair 对比卡片、相关分析图、source links 仍可用。
2. 新功能验证点：房地产预测趋势矩阵、房价趋势图、因子贡献图、关联分析图可渲染。
3. 边界情况：样本不足、单城市缺数据、某因子缺失、长期预测冲突信号。
4. 异常处理：provider 失败、SQLite 写入失败、API 返回 unavailable。
5. 配置兼容性：未开启实时数据时使用 sample fallback；旧 Macro payload 字段保持兼容。

## 11. 风险与后续建议

- 官方页面结构变化会影响实时抓取，因此第一版必须保留 sample fallback 和明确的数据状态。
- 全国整体等权聚合不等同于官方全国房价指数，页面应标注为模型聚合口径。
- 5 年、10 年和长期趋势应持续表达为结构判断，避免输出精确涨跌幅。
- 后续可引入库存、土地成交、人口流入、租金收益率和房价收入比，增强长期模型解释力。

