# Task 06 Fishbowl Rules And Panel Protocol

## 跟踪标的

- CSI 300
- CSI 500
- CSI 1000
- SSE Composite
- ChiNext
- Hang Seng Tech

## 输入字段

- `trade_date`
- `close_price`
- `lookback_closes`

## 计算规则

- `ma20 = last 20 closes average`
- `deviation_pct = (close - ma20) / ma20 * 100`

## 鱼盆状态

- `breakout`: 偏离度 `>= +3%`
- `constructive`: 偏离度 `[0%, +3%)`
- `neutral`: 偏离度 `[-3%, 0%)`
- `pressured`: 偏离度 `< -3%`
- `unavailable`: 历史样本不足或 provider 无数据

## 面板协议

每张卡至少包含：

- `key`
- `label`
- `trade_date`
- `close_value`
- `ma20_value`
- `deviation_pct`
- `fishbowl_state`
- `explanation`
- `source_label`
- `status`
