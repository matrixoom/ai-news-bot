# Task 02 Provider Contracts

## 目标

把任务 2 的“主源 / 备源 / 降级策略”沉淀为后续实现可直接承接的契约，而不是停留在文档层。

## Provider 列表

### 1. `NewsProvider`

职责：

- 拉取科技、财经、时政新闻
- 统一返回标题、链接、发布时间、来源、分类
- 不负责去重排序策略

输入约束：

- 必须显式传入新闻分类
- 必须显式传入目标日期
- 必须支持 `limit`

输出约束：

- `published_at` 必须可解析
- `url` 必须是原始文章链接或稳定落地页
- `provider` 与 `source_name` 必须可追溯

### 2. `SearchProvider`

职责：

- 提供热点补全查询
- 返回候选结果和原始来源指针

输入约束：

- 必须显式传入 `query`
- 必须支持按目标日期过滤
- 必须限制最大返回量

输出约束：

- 结果不得直接作为最终事实
- 必须保留 `original_url`
- 若无发布时间，服务层必须把该结果降级为低可信候选

### 3. `MarketDataProvider`

职责：

- 拉取宽基指数收盘快照
- 返回收盘价、交易日、币种、来源链接

输入约束：

- 必须显式传入 `symbols`
- 必须显式传入 `trade_date`

输出约束：

- provider 只返回原始行情快照
- 20 日均线、鱼盆模型状态等派生值在服务层计算

### 4. `MacroDataProvider`

职责：

- 拉取宏观指标最新值
- 返回指标代码、数值、单位、发布时间、来源链接

输入约束：

- 必须显式传入指标代码列表

输出约束：

- 不允许返回缺少来源链接的主面板数据
- 必须保留原始发布时间和周期标签

### 5. `ResearchProvider`

职责：

- 拉取未来 7 / 30 / 90 / 180 天的事件和政策预告
- 返回结构化事件、可信度和来源集合

输入约束：

- 必须显式传入 `horizon`
- 必须显式传入查询主题
- 必须显式传入 `as_of` 日期

输出约束：

- 每条记录至少一个来源
- `confidence=low` 的记录不能直接进入主展示区
- 模型输出必须被约束为结构化 JSON 再进入领域层

## 统一运行语义

所有 provider 都必须实现：

- `provider_key`
- `healthcheck()`

健康检查只判断 provider 可用性，不判断业务完整性。

## 分层边界

- `app` 层不能直接 import 第三方数据 SDK
- `services` 层只能依赖 provider 契约和领域对象
- `providers` 层可以包裹现有 `src/news/*` 与未来 AKShare / 页面解析实现
- `delivery` 层只能消费服务层产出的结构化数据

## 第一阶段兼容策略

- 旧 `src/news/fetcher.py` 可先包装成 `NewsProvider` 兼容实现
- 旧 `src/news/web_search.py` 可先包装成 `SearchProvider` 兼容实现
- 旧 `src/llm_providers/*` 继续保留，后续迁移到新的 provider 分层

## 对应代码骨架

- 领域数据模型：`src/domain/external_data.py`
- Provider 契约：`src/providers/contracts.py`
- 主备源策略：`src/providers/strategy.py`
