# Macro Data 数据源文档

## GDP 数据

### 名义 GDP（现价）

| 频率 | 时间范围 | 数据来源 | 获取方式 | 字段 |
|------|---------|---------|---------|------|
| 年度 | 1960-2025 | World Bank API | `api.worldbank.org/v2/country/CHN/indicator/NY.GDP.MKTP.CN` | 人民币现价 |
| 季度 | 2006-2026 | 东方财富 / AkShare | `ak.macro_china_gdp()` → 累计值分解为当季值 | 国内生产总值-绝对值（累计，亿元） |
| 季度 | 1992-2005 | 国家统计局季度公报（编译） | `macro_data_historical.py` 硬编码 | 累计名义 GDP（亿元），经经济普查修订 |

### 实际 GDP（不变价）

| 频率 | 时间范围 | 数据来源 | 获取方式 | 字段 |
|------|---------|---------|---------|------|
| 年度 | 1960-2024 | World Bank API | `api.worldbank.org/v2/country/CHN/indicator/NY.GDP.MKTP.KN` | 人民币不变价（2015年基期） |
| 季度（锚点） | 2022-2024 | 中经网（NBS 镜像） | `www.chinairn.com/qgjdsj/moref1f2.shtml` 抓取 | 不变价当季值（亿元） |
| 季度（推导） | 1992-2021 | 名义占比分配 + 官方增速校准 | World Bank 年度实际值按名义 GDP 当季占比分配到季度 | 推导值 |

### 实际 GDP 增速（当季同比）

| 频率 | 时间范围 | 数据来源 | 说明 |
|------|---------|---------|------|
| 季度 | 2018-2024 | NBS 季度新闻发布会 | `macro_data_historical.py` 中 `_OFFICIAL_QUARTERLY_REAL_GROWTH` 字典，用于校准实际 GDP 水平值 |
| 季度（派生） | 1993-2024 | 从实际 GDP 季度水平值计算 | `(value_current / value_prev_year - 1) × 100` |

### 名义 GDP 增速（当季同比）

| 频率 | 时间范围 | 数据来源 | 说明 |
|------|---------|---------|------|
| 季度（派生） | 1993-2026 | 从名义 GDP 季度水平值计算 | `(value_current / value_prev_year - 1) × 100` |

## 数据派生逻辑

### 名义 GDP 当季值
1. AkShare 提供的是累计值（Q1、Q1-Q2、Q1-Q3、Q1-Q4）
2. Q1 当季值 = Q1 累计值
3. Q2 当季值 = Q1-Q2 累计值 - Q1 累计值
4. Q3 当季值 = Q1-Q3 累计值 - Q1-Q2 累计值
5. Q4 当季值 = Q1-Q4 累计值 - Q1-Q3 累计值
6. 历史数据（1992-2005）同理

### 实际 GDP 季度水平值
1. chinairn 提供 2022-2024 年不变价当季值，直接采用
2. 其他年份：World Bank 年度实际 GDP × (该季度名义当季值 / 该年名义当季值总和)
3. 对 2018-2024 年，使用官方季度实际增速做链式校准：
   - 从 chinairn 锚点向后链推：`level_q = level_same_q_next_year / (1 + growth_next/100)`
   - 从 chinairn 锚点向前链推：`level_q = level_same_q_prev_year × (1 + growth/100)`

### 实际 GDP 增速
1. 优先从校准后的实际 GDP 水平值计算同比增速
2. 确保与官方公布的季度同比增速一致

## 其他宏观指标

| 指标 | 时间范围 | 数据来源 | 获取方式 |
|------|---------|---------|---------|
| CPI | 月度 | AkShare | `ak.macro_china_cpi_monthly()` |
| PPI | 月度 | AkShare | `ak.macro_china_ppi()` |
| 社融 | 月度 | 央行 / AkShare | 待实现 |
| 信贷 | 月度/季度 | NBS / 央行 | 待实现 |
| 杠杆率 | 季度 | CNBS | `ak.macro_cnbs()` |

## 已知限制

1. **1992-1995 年季度数据**：此期间 NBS 仅公布年度 GDP，季度累计值为学术估计。实际 GDP 增速为年度平均分布。
2. **实际 GDP 季度值（1992-2021）**：通过名义占比分配法推导，在 GDP 平减指数剧烈波动时（如 2020-2021）可能与真实值有偏差，已通过官方增速校准修正。
3. **NBS API（data.stats.gov.cn）**：截至 2026-05-02 返回 403，无法直接访问。所有 NBS 数据通过 AkShare 和编译数据间接获取。
4. **World Bank 年度数据**：2025 年可能为估计值，2026 年尚未发布。

## 更新日期

2026-05-02
