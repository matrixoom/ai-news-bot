# Task 04 Domain Config And Summary Protocol

## 领域配置

当前新闻管线默认覆盖三个域：

- `technology`
- `finance`
- `policy`

每个域都包含：

- `display_name`
- `search_queries`
- `rss_limit`
- `search_limit`
- `summary_strategy`
- `official_sources`
- `priority_sources`

## Provider 使用方式

- `NewsProvider` 负责返回标准化 RSS / 新闻源记录
- `SearchProvider` 负责返回候选搜索结果
- 聚合服务只依赖 provider 契约，不依赖底层抓取实现

## 融合规则

### 当日过滤

- 只有包含“目标日期”记录的新闻组才能进入最终结果
- 未标注发布时间的搜索结果不会单独进入主面板
- 但如果该搜索结果与当日 RSS 新闻命中同一 dedupe key，可以作为交叉印证保留

### 去重

- 默认按标题规范化 + 链接兜底生成 `dedupe_key`
- RSS 与搜索命中相同 key 时会合并为一条

### 排序

排序优先级由以下因素组成：

- 是否当日
- 是否官方信源
- 是否一级信源
- 是否有多源交叉印证
- 是否有摘要文本
- RSS 相比搜索的基础稳定性

## 输出协议

每个域输出一个 `DomainNewsDigest`，包含：

- `category`
- `display_name`
- `query_templates`
- `summary_strategy`
- `candidate_count`
- `dropped_outdated_count`
- `merged_duplicate_count`
- `items`

每个 `NewsPipelineItem` 至少包含：

- `title`
- `category`
- `source_name`
- `source_type`
- `url`
- `published_at`
- `fetched_at`
- `raw_summary`
- `is_today`
- `dedupe_key`
- `source_weight`
- `corroboration_count`
- `score`
- `supporting_sources`

## 与后续任务的关系

- Task 05 / 06 继续把宏观与市场模块接入同样的服务层结构
- Task 08 直接复用 `NewsPipelineSnapshot` 做推送装配
- 后续 LLM 摘要只消费这里的结构化输出，不再直接面向原始 RSS 和搜索结果
