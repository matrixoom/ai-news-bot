# Task 05 Indicator Registry And Display Protocol

## 指标注册表

当前宏观注册表默认覆盖：

- `cpi`
- `ppi`
- `gdp_nominal`
- `gdp_real`
- `social_financing`
- `household_leverage`
- `government_leverage`

每个指标定义包含：

- `indicator_code`
- `display_name`
- `frequency`
- `unit`
- `source_label`
- `source_url`
- `provider_key`
- `update_rule`
- `display_hint`

## 标准化规则

### 频率

- 月度、季度、年度指标统一在注册表内定义
- 页面不根据 provider 自行猜测频率

### 数值

- 当前值与上期值统一格式化
- `change_value` 和 `change_kind` 用于输出同比 / 环比 / 较上期
- provider 未返回变化值时，服务层退化为仅展示当前值和上期值

### 趋势

- 优先使用 provider 返回的 `trend_summary`
- 否则根据变化值或最新值与上期值比较推导 `up / down / flat`
- 无法判断时标记 `unavailable`

## 页面展示协议

每张宏观卡至少包含：

- `key`
- `label`
- `value`
- `previous_value`
- `change_label`
- `trend`
- `source_label`
- `updated_at`
- `frequency`
- `context`
- `status`

## 降级策略

- provider 无法返回某个指标时，页面仍保留该指标卡
- 无数据卡必须展示来源、更新规则和不可用状态
- 新增指标只需更新注册表和 provider，不必改 Dashboard 核心结构

## 与后续任务的关系

- Task 06 可以直接消费这里的卡片展示协议
- 后续真实官方页面解析或 AKShare 接入时，只需要替换 `MacroDataProvider` 实现
