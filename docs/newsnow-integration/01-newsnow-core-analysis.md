# NewsNow 核心实现拆解

## 1. 核心思想

`newsnow` 的核心思想不是“一个大爬虫”，而是“源级插件化 + 源级缓存调度”：

1. 每个数据源是独立 getter，彼此解耦。
2. 每个源都有独立刷新间隔 `interval`，而不是全局统一刷新频率。
3. 缓存与抓取失败兜底一起设计，保证源不可用时仍可返回最近可用数据。
4. 数据层标准化输出 `NewsItem`，UI 只消费统一结构。

这套方法对“实时新闻”问题很有效，因为不同源更新频率差异很大，统一轮询会浪费资源且容易触发风控。

## 2. 关键方法

基于仓库 `server/api/s/index.ts`、`shared/pre-sources.ts`、`server/getters.ts`、`server/utils/source.ts` 可归纳出四个关键方法：

1. 源注册与元数据驱动。
2. 动态 getter 聚合。
3. 双层缓存判定。
4. 失败回退缓存。

### 2.1 源注册与元数据驱动

`shared/pre-sources.ts` 统一配置：

1. source id。
2. 分类列（tech/finance/china/world）。
3. 类型（realtime/hottest/none）。
4. 刷新间隔（最小可到 2 分钟）。

之后由脚本生成 `shared/sources.json` 供前后端共享，避免硬编码分叉。

### 2.2 动态 getter 聚合

`server/getters.ts` 使用 glob 自动加载 `server/sources` 下所有 getter 文件，形成 `id -> getter` 映射。新增源只需新增模块和配置，不需要改中心路由逻辑。

### 2.3 双层缓存判定

`server/api/s/index.ts` 中是“interval 优先于 TTL”的策略：

1. 若 `now - updated < source.interval`，直接返回缓存（快速、低成本）。
2. 若超过 interval，但仍在 TTL 内，按 `latest` 参数和登录状态决定是否强制刷新。
3. 若超过 TTL，触发实际抓取。

这个策略能兼顾实时性和稳定性。

### 2.4 失败回退缓存

抓取报错时：

1. 若已有缓存，返回缓存。
2. 若没有缓存，再抛错。

因此单源短时失败不会导致整个看板空白。

## 3. 实现结构总结

`newsnow` 在实时新闻部分的工程结构可以抽象为：

1. `source metadata`：定义“抓什么、多久抓一次、属于哪类”。
2. `source getter`：定义“怎么抓”。
3. `api controller`：定义“何时抓、何时复用缓存、失败怎么兜底”。
4. `unified item schema`：定义“对外统一返回什么字段”。

## 4. 对当前项目可借鉴点

最值得借鉴的不是具体某个爬虫，而是这三条策略：

1. 按源设置刷新周期，不用固定全局轮询。
2. 源级缓存复用，减少重复请求和外部依赖抖动。
3. 抓取失败优先回退旧缓存，保证上层服务可用性。
