# Task 01: Foundation And Content Pipeline

## 目标

先把项目底座补齐，否则后续接财经、时政、搜索、预告模块都会继续堆在脆弱链路上。

## 背景问题

- `enable_web_search` 现在没有真正进入生成链路
- RSS 抓取没有去重、时间过滤、排序、质量控制
- 新闻数据结构比较松散，后续扩域会越来越难维护
- 多语言、多模块报告现在是串行拼接，缺少明确的报告装配层

## 本阶段交付

- 统一新闻数据模型
- 统一采集管线
- 支持 RSS + Search 的混合采集
- 支持当日新闻过滤、去重、排序
- 引入报告装配层，为后续插入财经表格和预告模块做准备

## 任务拆解

### 1. 定义统一数据模型

建议新增以下领域对象：

- `NewsItem`
- `NewsBatch`
- `ReportSection`
- `ReportContext`

`NewsItem` 至少包含：

- `id`
- `domain`，如 `tech` / `finance` / `politics`
- `language`
- `title`
- `summary`
- `source_name`
- `source_url`
- `published_at`
- `fetched_at`
- `is_same_day`
- `quality_score`
- `dedupe_key`

### 2. 重构采集层

建议把当前 `NewsFetcher` 拆成：

- `RssCollector`
- `SearchCollector`
- `NewsNormalizer`
- `NewsDeduplicator`
- `NewsRanker`

目标不是一次做复杂，而是先把职责切开。

### 3. 接通搜索逻辑

当前要求不是“有搜索开关”，而是“真正得到当日热点”。

需要落实：

- 定义搜索查询模板
- 采集搜索结果
- 拉取原始页面或摘要信息
- 判断是否属于当日
- 和 RSS 结果去重合并

### 4. 建立时效过滤规则

至少实现以下规则：

- 优先保留发布日期为当日的内容
- 对没有明确发布时间的结果降低权重
- 对明显为旧闻翻炒的内容降权
- 对搜索结果与 RSS 的重复内容只保留一条主记录

### 5. 建立排序规则

初期可以采用规则打分，不必一开始就上复杂模型。

建议排序因素：

- 是否当日
- 来源权重
- 标题相关性
- 是否多个来源交叉提及
- 是否来自官方源 / 一级信源

### 6. 新建报告装配层

建议新增 `ReportBuilder`，职责是：

- 组织日报各个 section
- 控制 section 顺序
- 汇总 markdown 输出
- 给不同通知渠道提供统一正文

## 输出文件建议

- `src/models/news.py`
- `src/collectors/rss_collector.py`
- `src/collectors/search_collector.py`
- `src/collectors/pipeline.py`
- `src/report/builder.py`

## 验收标准

- 能输出“当日热点池”并打印结构化统计
- 同一新闻在 RSS 和搜索命中时不会重复进入摘要
- 非当日新闻默认不进入主摘要
- 生成链路不再直接依赖原始抓取结果字典

## 风险

- 搜索源质量参差不齐
- 发布时间字段缺失时，过滤规则可能误杀
- 如果继续沿用弱结构 prompt，后续模块会很难稳定组合

## 建议优先级

P0，必须先做。
