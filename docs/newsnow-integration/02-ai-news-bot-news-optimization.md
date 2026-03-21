# ai-news-bot 新闻链路优化说明

## 1. 现状问题

优化前 live 新闻链路主要是：

1. `PublicRssNewsProvider`（少量固定 RSS 源）。
2. `GoogleNewsSearchProvider`（查询补充）。

主要不足：

1. 覆盖面有限，源数量少。
2. 缺少“按源刷新间隔”策略，容易重复请求。
3. 缺少“源级缓存复用”语义，外部波动时稳定性不足。

## 2. 本次改造目标

1. 借鉴 `newsnow` 的实时抓取思路。
2. 整合 `newsnow` 当前全部 active 非 redirect 源（50 个）。
3. 保留现有 RSS 链路作为并行上游，避免单一依赖。
4. 不破坏现有 `NewsProvider` 合同和下游 `NewsPipelineService`。

## 3. 已落地实现

### 3.1 全量源注册表

新增：`src/providers/newsnow_sources.py`

1. 固化 50 个 active source id。
2. 保存 column/type/interval_ms 元数据。
3. 作为 NewsNow Provider 的统一配置输入。

### 3.2 NewsNow 聚合 Provider

新增：`src/providers/newsnow_provider.py`

核心能力：

1. `NewsNowAggregatedNewsProvider`
2. `CompositeNewsProvider`

`NewsNowAggregatedNewsProvider` 的关键机制：

1. 按源刷新间隔缓存（`source.interval_ms`）。
2. 并发拉取（线程池）。
3. 刷新失败时回退旧缓存。
4. 按分类轮转拉取 source（避免一次性请求全部源导致抖动）。
5. 统一归一化为 `NewsItem`。

### 3.3 分类映射

为兼容当前三类业务域，映射规则如下：

1. `tech -> NewsCategory.TECHNOLOGY`
2. `finance -> NewsCategory.FINANCE`
3. `china/world -> NewsCategory.POLICY`

说明：`china/world` 是较宽泛映射，用于把 NewsNow 全量源接入到现有三分类框架。后续可再做更细粒度主题过滤。

### 3.4 与现有 RSS 组合

改造：`src/services/dashboard_service.py`

live 模式新闻 Provider 从单一 RSS 变为组合模式：

1. `NewsNowAggregatedNewsProvider()`
2. `PublicRssNewsProvider()`
3. `CompositeNewsProvider((1,2))`
4. `FallbackNewsProvider(Composite, SampleNewsProvider())`

效果：

1. NewsNow 提供大规模多源覆盖。
2. 现有 RSS 提供稳定的官方/媒体补充。
3. 两路都失败时继续回退样例数据，保证页面可用。

### 3.5 Provider 导出

改造：`src/providers/__init__.py`

新增导出：

1. `NewsNowAggregatedNewsProvider`
2. `CompositeNewsProvider`

### 3.6 测试补充

新增：`tests/test_task04_newsnow_integration.py`

覆盖点：

1. 源间隔缓存命中时不重复请求。
2. 刷新失败回退旧缓存。
3. 组合 Provider 全失败抛错。
4. 组合 Provider 可合并成功上游结果。

### 3.7 可配置参数（环境变量）

`NewsNowAggregatedNewsProvider` 支持以下环境变量：

1. `NEWSNOW_BASE_URL`：NewsNow 服务地址，默认 `https://newsnow.busiyi.world`。
2. `NEWSNOW_TIMEOUT_SECONDS`：单次请求超时，默认 `4.0`。
3. `NEWSNOW_MAX_WORKERS`：并发抓取线程数，默认 `8`。
4. `NEWSNOW_MAX_ITEMS_PER_SOURCE`：每个源最多保留条数，默认 `3`。
5. `NEWSNOW_MIN_SOURCE_BUDGET`：每次最少拉取源数量，默认 `8`。
6. `NEWSNOW_SOURCE_BUDGET_MULTIPLIER`：按 `limit * multiplier` 计算轮转预算，默认 `2`。

## 4. 这次优化的核心收益

1. 覆盖面：从少量 RSS 扩展到 NewsNow 全量 active 源 + 原 RSS。
2. 稳定性：按源缓存 + 失败回退，降低外部源抖动影响。
3. 性能：轮转抓取 + 并发抓取，避免单次全量硬拉。
4. 可扩展性：源列表和抓取逻辑解耦，后续可继续精细化过滤和打分。
