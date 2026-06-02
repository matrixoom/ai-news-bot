# TrendInsight 事件洞察模块设计文档

## 1. 背景说明

TrendInsight 当前已经具备宏观数据、市场数据、趋势模型、推送中心、事件展望等模块。现有页面中，左侧导航包含 `Event Outlook` 分组，当前主要用于展示国内、国际维度的事件日历、重大会议、宏观节点、政策节点等信息。

现计划在 `Event Outlook` 模块下新增事件洞察能力，用于跟踪财经热点新闻、公告、财报、会议纪要、研报、行业报告等信息，从中抽取结构化事件，构建事件时间线和事件关系图，辅助用户还原热点主题的发酵路径，发现潜在投资研究线索。

必须明确区分两个业务域：

```text
现有 Event Outlook 国内 / 国际页面：
  面向未来将要发生的事件。
  本质是静态日历，用于跟踪会议、政策窗口、宏观节点和科技活动。

新增事件洞察页面：
  面向已经发布、导入或扫描到的研究材料。
  本质是证据发现与研究分析系统，用于抽取事实事件、构建主题时间线和关系图。
```

两者只共享左侧 `Event Outlook` 导航分组和整体视觉风格，不共享事件表、处理状态、Service、Repository 或 API 契约。新增能力不得改变现有静态日历的业务语义。

本模块的目标不是做短线热点追涨工具，也不是自动荐股系统，而是建设一个本地运行的投资研究辅助工具，核心是：

```text
证据发现
事件归纳
主题溯源
关系构建
发酵路径分析
```

第一阶段重点建设以下页面：

```text
Event Outlook
  ├── 国内
  ├── 国际
  ├── 事件列表
  ├── 主题溯源
  └── 事件关系图

System
  └── Settings
      └── 大模型配置
```

其中：

```text
事件列表页：展示每日扫描、导入、解析后的各类事件，是事件洞察模块的数据工作台。
主题溯源页：围绕某个主题还原事件发酵路径和证据链。
事件关系图页：围绕某个主题或事件展示事件之间的关系网络。
大模型配置页：为事件抽取、归纳、关系判断、主题摘要等能力提供模型配置入口。
```

---

## 2. 产品定位

本模块定位为：

```text
本地运行的金融事件证据发现系统。
```

它不是：

```text
不是自动荐股系统
不是短线追涨工具
不是纯新闻聚合器
不是舆情热度榜
不是商业化实时情报平台
```

它是：

```text
投资研究辅助工具
财经事件证据链管理工具
热点主题发酵路径分析工具
事件关系图谱分析工具
财经信息归纳与溯源工具
```

核心原则：

```text
MVP 不是简陋版。
第一阶段可以控制功能范围，但不能降低核心分析质量。
```

当前项目可以暂时不考虑：

```text
高并发
多用户权限
分布式部署
Kafka
Redis
商业级监控告警
音频/视频解析
复杂运维体系
```

但以下能力不能玩具化处理：

```text
事件抽取
事件归纳
事件聚类
事件去重
事件关系识别
主题发酵路径分析
证据链追溯
图谱展示
人工校正
大模型调用配置
```

---

## 3. 第一阶段建设目标

第一阶段建设一个高质量的垂直切片，而不是铺开全市场扫描。

优先围绕一个或少数主题跑通完整闭环，例如：

```text
内存涨价 / HBM / 存储芯片
光模块 / CPO
商业航天
黄金白银 / 有色金属
```

完整链路如下：

```text
原始材料入库
  ↓
创建可重试的处理任务
  ↓
全文检索 / 语义检索
  ↓
事件抽取
  ↓
事件标准化
  ↓
事件去重
  ↓
事件聚类
  ↓
主题归并
  ↓
事件关系识别
  ↓
证据链绑定
  ↓
Neo4j 图谱写入
  ↓
事件列表 / 主题溯源 / 事件关系图展示
```

耗时操作不得阻塞 HTTP 请求。导入、抽取、Embedding、聚类、主题分析、关系生成和图谱同步均通过本地异步任务执行，页面通过任务状态接口查询进度。

第一阶段核心交付页面：

```text
1. Event Outlook / 事件列表
2. Event Outlook / 主题溯源
3. Event Outlook / 事件关系图
4. System Settings / 大模型配置
```

---

## 4. 导航设计

### 4.1 Event Outlook 导航调整

当前左侧导航中已有：

```text
Event Outlook
  ├── 国内
  └── 国际
```

调整后建议为：

```text
Event Outlook
  ├── 国内
  ├── 国际
  ├── 事件列表
  ├── 主题溯源
  └── 事件关系图
```

路由建议优先沿用当前项目已有的 `tab` 模式，例如：

```text
/event-outlook?tab=domestic
/event-outlook?tab=international
/event-outlook?tab=events
/event-outlook?tab=topic-trace
/event-outlook?tab=event-graph
```

其中：

```text
tab=domestic / tab=international：
  继续渲染现有未来事件静态日历。
  继续使用现有 /api/frontend/modules/event-outlook 契约。

tab=events / tab=topic-trace / tab=event-graph：
  渲染新增事件洞察工作区。
  使用独立的 /api/frontend/modules/event-insight/* 契约。
```

`tab` 是页面工作区选择参数，不再等同于静态日历的 `region`。只有 `domestic` 和 `international` 两个工作区可以把 Tab 映射为日历 `region`。新增工作区不得把 `events`、`topic-trace` 或 `event-graph` 传入现有日历接口。

如果当前项目内部已有其他路由约定，应优先遵守现有实现，不强行改造路由体系。

### 4.2 System Settings 导航调整

当前系统底部存在：

```text
System
  └── Settings
```

建议在 Settings 中增加“大模型配置”页面或 Tab。

如果 Settings 当前是单页，则建议增加 Tab：

```text
Settings
  ├── 基础设置
  ├── 数据源配置
  └── 大模型配置
```

如果 Settings 当前已经有子路由，则按现有结构增加：

```text
System
  └── Settings
      └── 大模型配置
```

---

## 5. 页面风格适配要求

新增页面必须优先适配当前 TrendInsight 项目的已有风格。

不要在实现中写死某套全新的 UI 风格，不要强行引入与当前项目视觉体系不一致的组件风格。

从现有截图观察，当前项目大致具备以下特征：

```text
左侧分组导航
浅色背景
卡片式内容容器
大面积留白
低饱和度色彩
圆角卡片
轻量阴影
简洁数据展示
```

但设计文档不应强制规定具体颜色、间距、圆角数值、组件库、图标库。Codex 实现时应先检查当前项目已有组件、样式变量、布局容器、导航结构，并优先复用。

实现要求：

```text
1. 新增页面应复用当前项目已有 Layout、Sidebar、Card、Button、Table、Drawer、Modal 等基础组件。
2. 新增页面不应破坏国内/国际 Event Outlook 页面。
3. 页面视觉应与当前 TrendInsight 保持一致。
4. 不要强行引入新的 UI 框架。
5. 如果项目已有图表封装，应优先复用。
6. 如果项目已有通用筛选区、表格、抽屉、弹窗组件，应优先复用。
7. 只有在现有组件不能满足关系图需求时，才考虑引入或封装 AntV G6 / Cytoscape.js 等图谱组件。
```

---

# 6. 页面一：事件列表页

## 6.1 页面定位

事件列表页是事件洞察模块的数据工作台，用于展示每天扫描、导入、解析、抽取后的事件。

它不是普通新闻列表，而是：

```text
每日事件雷达
事件处理工作台
主题归纳前置入口
证据材料管理入口
```

它承接的数据包括：

```text
新闻
公告
财报
会议纪要
研报
行业报告
政策文件
宏观数据发布
商品价格变动
公司经营动态
机构观点
市场异动
```

本地文件存储就够了

你不需要 MinIO。

可以这样组织：

data/
├── raw/
│   ├── html/
│   ├── pdf/
│   ├── txt/
│   └── images/
├── parsed/
│   ├── markdown/
│   └── json/
├── exports/
└── trendinsight.db

数据库只存路径：

local_file_path = data/raw/pdf/xxx.pdf

这样简单、可备份、可迁移。

第一阶段暂不处理：

```text
音频
视频
直播
社媒短内容
复杂图表自动解析
```

---

## 6.2 页面目标

事件列表页需要回答：

```text
今天系统扫描到了哪些事件？
哪些事件已经结构化？
哪些事件还只是原始材料？
哪些事件可能归属于同一个主题？
哪些事件值得进一步分析？
哪些事件是重复、低质量或噪声？
哪些事件已经同步到事件图谱？
```

事件列表页和其他页面关系：

```text
事件列表页 → 选择事件或主题 → 主题溯源页
事件列表页 → 选择事件或主题 → 事件关系图页
```

---

## 6.3 页面布局

建议采用当前项目风格下的常规数据页布局：

```text
顶部：筛选区
中部：事件列表表格或卡片列表
右侧：事件详情抽屉
底部：分页与批量操作
```

具体 UI 实现应以当前项目已有页面风格为准。

---

## 6.4 筛选条件

事件列表页需要支持以下筛选：

```text
日期范围
来源类型
事件类型
处理状态
证据等级
重要性评分
置信度
是否已归入主题
是否已入图谱
关键词
实体
主题
```

来源类型：

```text
news
announcement
earnings_report
meeting_minutes
research_report
policy
industry_report
macro_data
market_move
other
```

事件类型：

```text
policy
price_change
supply_demand
order_contract
capacity
earnings
technology
capital_market
institution_view
macro
risk
other
```

---

## 6.5 列表字段

事件列表建议展示：

```text
事件标题
事件时间
发布时间
来源
材料类型
事件类型
相关实体
主题归属
重要性评分
新颖度评分
市场相关性评分
置信度
处理状态
证据等级
操作
```

列表需要区分三个维度，避免把材料解析、事件分析和图谱投影压成一个不可回退的状态字段：

```text
材料状态：
  pending / running / succeeded / failed

事件分析状态：
  extracted / deduplicated / clustered / topic_linked / relation_built / failed

图谱投影状态：
  pending / synced / failed / not_applicable

人工处置状态：
  active / ignored
```

列表默认展示事件分析状态；详情抽屉同时展示材料状态、图谱投影状态和最近失败原因。

---

## 6.6 事件详情抽屉

点击事件后，打开详情抽屉，展示：

```text
事件标题
事件摘要
事件类型
事件时间
发布时间
来源名称
来源链接
原始材料入口
证据片段
相关实体
相关主题
相关事件
模型抽取结果
评分信息
处理状态
人工备注
操作日志
```

操作能力：

```text
编辑事件
查看原始材料
归入已有主题
创建新主题
标记为关键事件
标记为早期信号
标记为市场确认
标记为风险事件
标记为噪声
重新抽取
重新聚类
同步到图谱
```

---

## 6.7 批量操作

事件列表页需要支持批量处理：

```text
批量归入主题
批量忽略
批量重新抽取
批量重新聚类
批量同步图谱
批量导出
```

批量操作需要记录操作日志。

---

# 7. 页面二：主题溯源页

## 7.1 页面定位

主题溯源页用于回答：

```text
一个热点主题是如何从早期信号逐步发酵成市场关注的？
```

用户输入一个主题，例如：

```text
内存涨价
HBM
光模块
商业航天
黄金白银
有色金属
```

系统需要输出：

```text
主题摘要
发酵阶段判断
事件时间线
最早信号
关键催化事件
市场确认事件
支撑证据
反证和风险
相关实体
相关材料来源
```

---

## 7.2 页面布局

建议采用当前项目风格下的研究分析页布局：

```text
顶部：主题输入与筛选区
中部：主题摘要与阶段判断
下部：事件发酵时间线
侧边或抽屉：事件详情与证据链
```

具体样式应服从当前项目已有风格，不在代码中硬编码过细样式。

---

## 7.3 主题检索区

需要支持：

```text
主题关键词输入
时间范围选择
事件类型筛选
来源类型筛选
置信度筛选
重新分析按钮
保存主题按钮
```

输入主题后，系统执行混合召回：

```text
FTS5 关键词召回
sqlite-vec 语义召回
Neo4j 图谱扩展
结构化实体匹配
```

例如用户输入：

```text
内存涨价
```

系统可以扩展相关词：

```text
内存
存储
DRAM
NAND
HBM
存储芯片
涨价
报价
合约价
原厂
三星
SK海力士
美光
AI服务器
```

---

## 7.4 主题摘要区

展示：

```text
主题名称
主题摘要
当前发酵阶段
核心投资叙事
早期信号数量
关键催化数量
市场确认数量
反证风险数量
相关实体数量
相关材料数量
置信度
```

主题摘要必须基于已入库证据生成，不能让大模型凭空生成。

---

## 7.5 发酵阶段

主题阶段建议分为：

```text
噪声期
种子期
验证期
扩散期
共识期
分歧期
```

阶段判断依据：

```text
事件数量变化
事件来源数量变化
事件类型分布
高等级证据数量
机构观点数量
市场确认事件数量
反证风险数量
相关实体扩散程度
事件关系图密度
```

阶段解释：

```text
噪声期：事件少，来源少，关系弱，无明显市场响应。
种子期：出现多个弱信号，但尚未形成清晰叙事。
验证期：价格、订单、政策、供需数据开始互相印证。
扩散期：媒体、机构、市场开始集中讨论。
共识期：板块行情明显，资金关注度高，新闻密度高。
分歧期：利好兑现、估值争议、反证事件增多。
```

---

## 7.6 事件时间线

事件时间线按 `event_time` 排序，而不是简单按新闻发布时间排序。

每个时间线节点展示：

```text
事件标题
事件时间
事件类型
摘要
重要性评分
置信度
证据数量
来源等级
是否关键节点
是否反证事件
```

节点角色：

```text
early_signal
key_catalyst
market_confirmation
supporting_event
risk_event
follow_up
noise
```

实现时可根据当前项目风格选择适合的时间线组件，不强制具体 UI 方案。

---

## 7.7 关键节点识别

系统需要识别：

```text
最早信号
关键催化
市场确认
反证风险
后续进展
```

识别逻辑：

```text
最早信号：
  时间靠前
  主题相关度高
  当时关注度低
  后续被多个事件验证

关键催化：
  事件重要性高
  证据等级高
  事件之后主题热度明显上升
  与多个后续事件形成关系

市场确认：
  事件与行情变化、成交放大、板块上涨、商品价格变化等有关

反证风险：
  与主线叙事冲突
  指向需求不及预期、价格下跌、政策风险、估值过高、业绩不兑现等
```

---

## 7.8 证据链展示

每个事件必须可以展开查看证据链：

```text
原始标题
来源名称
来源链接
发布时间
证据片段
证据等级
原始正文入口
```

证据等级：

```text
A：官方公告、财报、政策文件、交易所数据、统计局/央行/海关数据
B：主流财经媒体、权威机构研报、产业数据
C：普通媒体、行业网站、专家访谈
D：社媒、论坛、传言、未验证信息
```

---

## 7.9 人工校正

主题溯源页必须支持人工校正：

```text
修改事件标题
修改事件时间
修改事件类型
标记为关键催化
标记为早期信号
标记为市场确认
标记为反证风险
从主题中移除事件
合并重复事件
添加人工备注
```

人工校正结果需要写入数据库，并优先于模型结果。

---

# 8. 页面三：事件关系图页

## 8.1 页面定位

事件关系图页用于回答：

```text
一个主题内部的事件之间如何连接？
哪些事件是核心节点？
哪些事件只是外围噪声？
哪些事件构成了发酵路径？
哪些事件是支撑、因果、反证、后续进展？
```

它不是普通知识图谱展示，而是面向投资研究的事件网络分析页面。

---

## 8.2 页面布局

建议采用：

```text
顶部：筛选区
主体：事件关系图
侧边：节点/边详情抽屉
底部或侧边：路径追踪结果
```

具体布局以当前项目已有风格为准，不强制固定。

---

## 8.3 筛选能力

需要支持：

```text
主题选择
时间范围
关系类型
事件类型
实体筛选
置信度阈值
图谱深度
布局方式
```

关系类型：

```text
same_topic
cause
support
contradict
follow_up
```

产业链关系通过实体筛选和实体边展示，不作为事件到事件的关系类型。

---

## 8.4 图谱节点

第一阶段主要展示：

```text
Event
Topic
Entity
```

后续可扩展：

```text
Stock
Industry
Concept
Commodity
Source
```

节点大小可由以下指标决定：

```text
importance_score
heat_score
market_relevance_score
degree
```

具体视觉编码应根据当前项目风格适配。

---

## 8.5 图谱关系

关系类型：

```text
(:Event)-[:BELONGS_TO]->(:Topic)
(:Event)-[:MENTIONS]->(:Entity)
(:Event)-[:CAUSES]->(:Event)
(:Event)-[:SUPPORTS]->(:Event)
(:Event)-[:CONTRADICTS]->(:Event)
(:Event)-[:FOLLOW_UP]->(:Event)
(:Event)-[:SAME_TOPIC]->(:Event)
(:Entity)-[:SUPPLY_CHAIN]->(:Entity)
```

边属性：

```text
relation_type
relation_summary
strength_score
confidence_score
evidence
generation_method
manual_confirmed
```

边详情中的 evidence 来自 `relation_evidence -> evidence`，必须展示可定位证据片段，不保存无法回溯的自由文本副本。

`generation_method` 可取：

```text
rule
llm
manual
hybrid
```

---

## 8.6 节点详情

点击事件节点，展示：

```text
事件标题
事件摘要
事件时间
发布时间
事件类型
重要性评分
新颖度评分
市场相关性评分
置信度
生命周期阶段
相关实体
所属主题
证据来源
人工备注
```

操作：

```text
查看原始材料
标记关键事件
编辑事件
从图中隐藏
添加关系
删除关系
```

---

## 8.7 边详情

点击关系边，展示：

```text
源事件
目标事件
关系类型
关系说明
强度评分
置信度
证据文本
生成方式
是否人工确认
```

操作：

```text
修改关系类型
调整强度
确认关系
删除关系
添加备注
```

---

## 8.8 路径追踪

支持从一个事件追踪到另一个事件：

```text
事件 A → 事件 B → 事件 C → 事件 D
```

Neo4j 查询示例：

```cypher
MATCH path = (start:Event {id: $startEventId})
  -[:CAUSES|SUPPORTS|CONTRADICTS|FOLLOW_UP*1..5]->
  (end:Event {id: $endEventId})
WHERE ALL(node IN nodes(path) WHERE single(other IN nodes(path) WHERE other = node))
RETURN path
LIMIT 10
```

查询必须同时限制主题范围和 `maxDepth`。页面需要展示每一步的关系类型和证据。

---

# 9. 大模型配置页

## 9.1 页面背景

当前系统还没有统一的大模型接入配置能力，但事件洞察模块依赖大模型完成：

```text
事件抽取
事件摘要
实体识别
证据提取
主题归纳
事件关系判断
主题阶段判断
反证风险识别
```

因此需要在 `System -> Settings` 中增加大模型配置能力。

注意：项目中可能已经存在历史原因形成的 LLM 接入方法、工具类、客户端封装或配置方式。实现前必须先调研当前代码中已有 LLM 相关实现，优先复用已有能力，避免重复造轮子。

Codex 实现前需要搜索项目中可能存在的：

```text
llm
LLM
openai
OpenAI
deepseek
qwen
chat
completion
embedding
ai
model
apiKey
baseUrl
```

如果已有历史 LLM 接入方法，应优先复用或适配，不要直接新建一套完全独立的调用链。只有在现有实现无法满足事件洞察模块需求时，才新增统一封装层。

当前仓库已经确认存在两条历史调用链，后续实现必须纳入迁移范围：

```text
通用新闻生成调用链：
  src/llm_providers/base_provider.py
  src/llm_providers/openai_provider.py
  src/llm_providers/deepseek_provider.py
  src/news/generator.py

现有未来事件日历研究采集调用链：
  src/providers/live_data.py
  ArkResearchProvider
```

迁移顺序：

```text
1. 扩展现有 BaseLLMProvider 能力，支持 base_url、超时、结构化输出和 Embedding。
2. 新增统一 LlmTaskRouter，承接事件洞察的任务级模型映射。
3. 让 ArkResearchProvider 适配统一客户端工厂，但保持现有未来事件日历输出契约不变。
4. 逐步让历史 NewsGenerator 复用统一客户端工厂。
5. 禁止事件洞察业务代码直接实例化第三套 OpenAI 客户端。
```

---

## 9.2 配置页目标

大模型配置页用于管理：

```text
模型供应商
API Key
Base URL
模型名称
默认聊天模型
默认抽取模型
默认关系判断模型
默认 Embedding 模型
超时时间
最大 Token
温度参数
是否启用
连接测试
任务级模型映射
```

需要支持多供应商、多模型，并允许不同任务使用不同模型。

例如：

```text
事件抽取：deepseek-chat / qwen-plus / gpt-4.1-mini
摘要归纳：deepseek-chat
关系判断：gpt-4.1 / qwen-max
Embedding：text-embedding-3-small / bge-m3 / qwen-embedding
```

---

## 9.3 接入方式

第一阶段至少支持 OpenAI Compatible API。

即通过：

```text
base_url
api_key
model
```

接入兼容服务。

理论上可覆盖：

```text
OpenAI
DeepSeek
通义千问 OpenAI 兼容模式
智谱 OpenAI 兼容模式
硅基流动
Ollama OpenAI 兼容接口
LM Studio
vLLM
其他兼容 OpenAI API 的服务
```

如果项目已有其他 LLM 调用方式，应优先复用其抽象模型，不强制只能使用 OpenAI Compatible 方式。

---

## 9.4 页面布局

页面风格应适配当前 Settings 模块。

建议包含：

```text
模型供应商配置
任务模型映射
连接测试
调用日志概览
```

### 模型供应商列表

字段：

```text
名称
Provider 类型
Base URL
默认 Chat Model
默认 Embedding Model
状态
最近测试时间
操作
```

### 新增/编辑配置

字段：

```text
配置名称
Provider 类型
Base URL
API Key
Chat Model
Embedding Model
Temperature
Max Tokens
Timeout Seconds
是否启用
备注
```

### 任务模型映射

任务类型：

```text
event_extraction
topic_summary
relation_judgement
risk_detection
lifecycle_stage_judgement
embedding
```

---

## 9.5 安全要求

API Key 不能明文展示。

要求：

```text
API Key 入库前加密
页面只显示脱敏结果
编辑时允许重新输入
接口返回不得包含明文 API Key
日志不得打印 API Key
连接测试失败时不得泄露完整请求头
```

脱敏展示：

```text
sk-****abcd
```

如果项目已有配置加密方案，应优先复用。

如果没有，至少使用本地轻量加密：

```text
使用本地配置密钥加密 API Key
密钥放在本地 .env 或系统环境变量
数据库只存密文
```

---

## 9.6 后端服务设计

建议抽象统一调用层，但需优先兼容历史实现。

推荐服务结构：

```text
LlmConfigService
LlmClientFactory
LlmClient
OpenAiCompatibleClient
LlmTaskRouter
PromptTemplateService
LlmCallLogService
```

职责：

```text
LlmConfigService：读取、保存、加密配置
LlmClientFactory：根据 provider 创建客户端
LlmTaskRouter：根据 task_type 找到模型配置
PromptTemplateService：统一管理 prompt
LlmCallLogService：记录 token、耗时、错误
```

事件洞察模块不得在业务代码中直接拼供应商 API 请求。

正确调用方式：

```text
EventExtractionService
  ↓
LlmTaskRouter.call(taskType = event_extraction, prompt, schema)
  ↓
LlmClient
```

如果项目已有类似封装，则直接适配已有封装。

---

## 9.7 Prompt 管理

Prompt 不要散落在业务代码中。

建议集中管理：

```text
prompts/
  event_extraction.md
  topic_summary.md
  relation_judgement.md
  risk_detection.md
  lifecycle_stage_judgement.md
```

每个 prompt 应有版本号。

如果项目已有 prompt 管理方式，应优先复用。

---

## 9.8 大模型失败处理

失败场景：

```text
API Key 错误
Base URL 错误
模型不存在
请求超时
返回非 JSON
JSON Schema 校验失败
限流
网络异常
```

处理要求：

```text
错误要记录到 llm_call_log
前端提示明确原因
事件处理状态标记为 failed
支持重新抽取/重新分析
不得吞异常
不得生成伪结果
```

---

# 10. 技术架构

## 10.1 第一阶段技术栈

建议：

```text
SQLite
SQLite FTS5
sqlite-vec
Neo4j Community
本地文件目录
大模型 API / 历史 LLM 接入能力
前端图谱组件
```

暂不引入：

```text
Kafka
Redis
Elasticsearch
MinIO
Milvus
Qdrant
音频/视频处理
```

---

## 10.2 组件职责

| 组件         | 职责                        |
| ---------- | ------------------------- |
| SQLite     | 事实主库，保存原始材料、事件、主题、实体、任务状态 |
| FTS5       | 关键词和全文检索                  |
| sqlite-vec | 语义检索、相似事件召回               |
| Neo4j      | 事件关系图谱、路径查询、子图查询          |
| 本地文件目录     | 保存原始 HTML、PDF、TXT、图片等材料   |
| 大模型        | 事件抽取、关系判断、摘要归纳、阶段判断       |
| 前端图组件      | 展示事件网络和发酵路径               |

---

## 10.3 数据流

```text
用户输入主题 / URL / 文本 / 文件
  ↓
保存 raw_document
  ↓
写入 FTS5
  ↓
生成 embedding，写入 sqlite-vec
  ↓
大模型抽取 event/entity/evidence
  ↓
事件去重与聚类
  ↓
生成 topic_event
  ↓
生成 event_relation
  ↓
同步 Neo4j
  ↓
页面展示
```

---

## 10.4 领域边界

现有静态日历和新增事件洞察必须保持独立：

| 领域 | 业务含义 | SQLite 主表 | Service / Repository | 前端接口 |
| --- | --- | --- | --- | --- |
| 未来事件静态日历 | 跟踪未来会议、政策窗口、宏观节点和科技活动 | 现有 `timeline_events` | 现有 `EventsOutlookService`、`EventsOutlookStore` | 现有 `/api/frontend/modules/event-outlook` |
| 事件洞察 | 从已发布材料中抽取事实事件并构建研究证据链 | 新增 `raw_document`、`event`、`topic`、`event_relation` 等表 | 新增 `EventInsightService`、`EventInsightRepository` | 新增 `/api/frontend/modules/event-insight/*` |

不得把新增事件洞察字段写入现有 `timeline_events`，也不得让静态日历接口承担材料抽取、聚类或图谱同步职责。

---

## 10.5 本地异步任务

第一阶段不引入 Kafka、Redis 或外部任务队列。使用 SQLite 持久化任务和应用内后台 worker：

```text
Controller
  ↓ 创建 processing_job，返回 202 + jobId
EventInsightJobWorker
  ↓ 原子领取 pending 任务
Service
  ↓ 执行单个阶段
Repository
  ↓ 提交事实数据、任务状态和下一阶段任务
```

任务类型：

```text
parse_document
extract_event
generate_embedding
deduplicate_event
cluster_topic
analyze_topic
build_relation
sync_graph
rebuild_graph_projection
```

任务要求：

```text
1. 每个任务必须有 idempotency_key，客户端重试和 worker 重启不得生成重复事实。
2. 任务状态统一为 pending / running / succeeded / failed / cancelled。
3. 失败任务记录 error_code、error_message、attempt_count 和 next_retry_at。
4. LLM 限流、超时和临时网络错误允许指数退避重试；JSON Schema 校验失败允许有限次数重试。
5. 人工触发重新抽取或重新分析时创建新的 analysis_run，不直接覆盖历史结果。
6. 应用重启后，超过租约时间的 running 任务可以重新领取。
```

---

## 10.6 图谱投影一致性

SQLite 是唯一事实主库。Neo4j 只保存可重建的关系投影，不得成为页面基础事实的唯一来源。

```text
SQLite 事实事务提交
  ↓
同一事务写入 graph_sync_outbox
  ↓
后台 worker 幂等消费 outbox
  ↓
写入 Neo4j
  ↓
更新投影版本和同步状态
```

降级要求：

```text
1. Neo4j 不可用时，事件列表、事件详情、主题时间线和人工校正仍可使用。
2. 图谱页展示明确的降级提示，不返回伪造关系。
3. 支持从 SQLite 全量重建 Neo4j 投影。
4. 支持按 aggregate_type + aggregate_id + projection_version 巡检投影一致性。
5. outbox 消费失败不得回滚已经提交的 SQLite 事实。
```

---

## 10.7 时间与时区

数据库时间字段统一保存 ISO 8601 UTC 时间；仅表示自然日的字段保存 `YYYY-MM-DD`。前端展示时间时必须转换为浏览器本地时区，优先复用：

```text
frontend/src/shared/utils/format-local-date-time.ts
```

---

## 10.8 导入边界与本地文件安全

第一阶段支持：

```text
URL 导入
纯文本粘贴
本地文件导入：HTML / PDF / TXT / Markdown
扫描源批量导入
```

约束：

```text
1. 校验 MIME、文件扩展名、文件大小和内容哈希。
2. 原始文件统一复制到受控的数据目录，数据库只保存相对路径。
3. 禁止根据用户输入拼接任意本地路径，禁止路径穿越。
4. 对 PDF 第一阶段只提取文本，不做复杂图表识别。
5. source_url 规范化后参与去重；空 URL 不建立唯一约束。
```

---

## 10.9 后端分层

新增事件洞察必须遵守 Controller / Service / Repository 三层：

```text
Controller：
  参数校验、错误码映射、traceId 注入、HTTP 响应转换

Service：
  材料导入、任务编排、事件抽取、证据绑定、聚类、人工修订、图谱投影协调

Repository：
  SQLite 事务、查询、migration、FTS5、sqlite-vec 和 outbox 持久化
```

Neo4j 单独封装为 `EventGraphProjectionRepository`，只能消费 SQLite outbox 或执行只读图谱查询，不得绕过 SQLite 直接成为事实写入入口。

---

# 11. 数据库设计

## 11.1 raw_document

```sql
CREATE TABLE IF NOT EXISTS raw_document (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT,
    source_name TEXT,
    source_url TEXT,
    normalized_source_url TEXT,
    source_type TEXT,
    material_type TEXT,
    publish_time TEXT,
    crawl_time TEXT DEFAULT CURRENT_TIMESTAMP,
    content_hash TEXT UNIQUE,
    local_file_path TEXT,
    scan_batch_id INTEGER,
    parse_status TEXT DEFAULT 'pending',
    extraction_status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY(scan_batch_id) REFERENCES scan_batch(id),
    CHECK (parse_status IN ('pending', 'running', 'succeeded', 'failed')),
    CHECK (extraction_status IN ('pending', 'running', 'succeeded', 'failed'))
);
```

`normalized_source_url` 仅在非空时参与唯一索引：

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_document_normalized_source_url
ON raw_document(normalized_source_url)
WHERE normalized_source_url IS NOT NULL AND normalized_source_url <> '';
```

---

## 11.2 raw_document_fts

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS raw_document_fts USING fts5(
    title,
    content,
    source_name,
    content='raw_document',
    content_rowid='id',
    tokenize='unicode61'
);
```

外部内容 FTS 表必须通过触发器与事实表同步：

```sql
CREATE TRIGGER IF NOT EXISTS raw_document_ai AFTER INSERT ON raw_document BEGIN
    INSERT INTO raw_document_fts(rowid, title, content, source_name)
    VALUES (new.id, new.title, new.content, new.source_name);
END;

CREATE TRIGGER IF NOT EXISTS raw_document_ad AFTER DELETE ON raw_document BEGIN
    INSERT INTO raw_document_fts(raw_document_fts, rowid, title, content, source_name)
    VALUES ('delete', old.id, old.title, old.content, old.source_name);
END;

CREATE TRIGGER IF NOT EXISTS raw_document_au AFTER UPDATE ON raw_document BEGIN
    INSERT INTO raw_document_fts(raw_document_fts, rowid, title, content, source_name)
    VALUES ('delete', old.id, old.title, old.content, old.source_name);
    INSERT INTO raw_document_fts(rowid, title, content, source_name)
    VALUES (new.id, new.title, new.content, new.source_name);
END;
```

第一阶段必须先验证 `unicode61` 对中文标题和正文的召回效果。如果无法满足中文关键词搜索，优先增加应用层 n-gram 辅助索引或受控分词，不在第一阶段引入 Elasticsearch。

---

## 11.3 event

```sql
CREATE TABLE IF NOT EXISTS event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    summary TEXT,
    event_type TEXT,
    event_time TEXT,
    publish_time TEXT,
    sentiment TEXT,
    impact_direction TEXT,
    importance_score REAL DEFAULT 0,
    novelty_score REAL DEFAULT 0,
    market_relevance_score REAL DEFAULT 0,
    confidence_score REAL DEFAULT 0,
    lifecycle_stage TEXT,
    process_status TEXT DEFAULT 'extracted',
    is_key_event INTEGER DEFAULT 0,
    is_early_signal INTEGER DEFAULT 0,
    is_market_confirmation INTEGER DEFAULT 0,
    is_risk_event INTEGER DEFAULT 0,
    ignored INTEGER DEFAULT 0,
    ignore_reason TEXT,
    archived_at TEXT,
    canonical_event_id INTEGER,
    revision_no INTEGER DEFAULT 1,
    score_version TEXT DEFAULT 'v1',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY(canonical_event_id) REFERENCES event(id),
    CHECK (process_status IN ('extracted', 'deduplicated', 'clustered', 'topic_linked', 'relation_built', 'failed')),
    CHECK (importance_score >= 0 AND importance_score <= 1),
    CHECK (novelty_score >= 0 AND novelty_score <= 1),
    CHECK (market_relevance_score >= 0 AND market_relevance_score <= 1),
    CHECK (confidence_score >= 0 AND confidence_score <= 1)
);
```

`canonical_event_id` 用于表达已确认的重复事件归并。归并时不得删除原事件，确保可以撤销和追溯。

---

## 11.4 event_fts

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS event_fts USING fts5(
    title,
    summary,
    event_type,
    content='event',
    content_rowid='id',
    tokenize='unicode61'
);
```

`event_fts` 同样必须配置插入、更新、删除触发器，触发器结构与 `raw_document_fts` 一致。

---

## 11.5 event_source

```sql
CREATE TABLE IF NOT EXISTS event_source (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    raw_document_id INTEGER NOT NULL,
    confidence_score REAL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(event_id) REFERENCES event(id),
    FOREIGN KEY(raw_document_id) REFERENCES raw_document(id),
    UNIQUE(event_id, raw_document_id)
);
```

`event_source` 只表达事件与原始材料的来源关系。可定位的证据片段独立保存，避免关系证据退化成无法回溯的文本副本。

---

## 11.6 evidence

```sql
CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_document_id INTEGER NOT NULL,
    evidence_text TEXT NOT NULL,
    evidence_level TEXT NOT NULL,
    text_hash TEXT NOT NULL,
    page_number INTEGER,
    paragraph_index INTEGER,
    start_offset INTEGER,
    end_offset INTEGER,
    extraction_method TEXT NOT NULL,
    analysis_run_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(raw_document_id) REFERENCES raw_document(id),
    FOREIGN KEY(analysis_run_id) REFERENCES analysis_run(id),
    CHECK (evidence_level IN ('A', 'B', 'C', 'D')),
    UNIQUE(raw_document_id, text_hash, start_offset, end_offset)
);

CREATE TABLE IF NOT EXISTS event_evidence (
    event_id INTEGER NOT NULL,
    evidence_id INTEGER NOT NULL,
    relevance_score REAL DEFAULT 0,
    PRIMARY KEY(event_id, evidence_id),
    FOREIGN KEY(event_id) REFERENCES event(id),
    FOREIGN KEY(evidence_id) REFERENCES evidence(id)
);
```

证据定位优先级：

```text
PDF：page_number + paragraph_index + 字符偏移
HTML / TXT / Markdown：paragraph_index + 字符偏移
无法可靠定位时：至少保存 evidence_text + text_hash + raw_document_id
```

---

## 11.7 entity

```sql
CREATE TABLE IF NOT EXISTS entity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    normalized_name TEXT,
    entity_type TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);
```

同一实体必须通过规范化名称和别名归并：

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_normalized_name_type
ON entity(normalized_name, entity_type);

CREATE TABLE IF NOT EXISTS entity_alias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(entity_id) REFERENCES entity(id),
    UNIQUE(normalized_alias, entity_id)
);
```

实体类型：

```text
company
stock
industry
concept
commodity
policy
organization
person
location
product
macro_indicator
```

---

## 11.8 event_entity

```sql
CREATE TABLE IF NOT EXISTS event_entity (
    event_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    role TEXT,
    relevance_score REAL DEFAULT 0,
    PRIMARY KEY(event_id, entity_id),
    FOREIGN KEY(event_id) REFERENCES event(id),
    FOREIGN KEY(entity_id) REFERENCES entity(id)
);
```

---

## 11.9 topic

```sql
CREATE TABLE IF NOT EXISTS topic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    summary TEXT,
    lifecycle_stage TEXT,
    heat_score REAL DEFAULT 0,
    momentum_score REAL DEFAULT 0,
    early_signal_score REAL DEFAULT 0,
    confidence_score REAL DEFAULT 0,
    score_version TEXT DEFAULT 'v1',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);
```

---

## 11.10 topic_event

```sql
CREATE TABLE IF NOT EXISTS topic_event (
    topic_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    relevance_score REAL DEFAULT 0,
    role_in_topic TEXT,
    PRIMARY KEY(topic_id, event_id),
    FOREIGN KEY(topic_id) REFERENCES topic(id),
    FOREIGN KEY(event_id) REFERENCES event(id),
    CHECK (role_in_topic IN ('early_signal', 'key_catalyst', 'market_confirmation', 'supporting_event', 'risk_event', 'follow_up', 'noise'))
);
```

`role_in_topic` 可取：

```text
early_signal
key_catalyst
market_confirmation
supporting_event
risk_event
follow_up
noise
```

---

## 11.11 event_relation

```sql
CREATE TABLE IF NOT EXISTS event_relation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_event_id INTEGER NOT NULL,
    target_event_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,
    relation_summary TEXT,
    strength_score REAL DEFAULT 0,
    confidence_score REAL DEFAULT 0,
    generation_method TEXT,
    manual_confirmed INTEGER DEFAULT 0,
    revision_no INTEGER DEFAULT 1,
    archived_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY(source_event_id) REFERENCES event(id),
    FOREIGN KEY(target_event_id) REFERENCES event(id),
    UNIQUE(source_event_id, target_event_id, relation_type),
    CHECK (source_event_id <> target_event_id),
    CHECK (relation_type IN ('same_topic', 'cause', 'support', 'contradict', 'follow_up')),
    CHECK (generation_method IN ('rule', 'llm', 'manual', 'hybrid')),
    CHECK (strength_score >= 0 AND strength_score <= 1),
    CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

CREATE TABLE IF NOT EXISTS relation_evidence (
    relation_id INTEGER NOT NULL,
    evidence_id INTEGER NOT NULL,
    relevance_score REAL DEFAULT 0,
    PRIMARY KEY(relation_id, evidence_id),
    FOREIGN KEY(relation_id) REFERENCES event_relation(id),
    FOREIGN KEY(evidence_id) REFERENCES evidence(id)
);
```

关系类型：

```text
same_topic
cause
support
contradict
follow_up
```

`same_topic` 可以从 `topic_event` 推导，默认不主动写入；只有需要固定人工判断时才保存。产业链关系优先表达为实体之间的关系，避免事件图同时承担产业知识图谱职责。

---

## 11.12 scan_batch

```sql
CREATE TABLE IF NOT EXISTS scan_batch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_name TEXT,
    scan_date TEXT,
    source_scope TEXT,
    status TEXT DEFAULT 'pending',
    total_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled'))
);
```

---

## 11.13 event_operation_log

```sql
CREATE TABLE IF NOT EXISTS event_operation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER,
    operation_type TEXT NOT NULL,
    field_name TEXT,
    before_value TEXT,
    after_value TEXT,
    operation_detail TEXT,
    reason TEXT,
    analysis_run_id INTEGER,
    operator TEXT DEFAULT 'local_user',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(event_id) REFERENCES event(id),
    FOREIGN KEY(analysis_run_id) REFERENCES analysis_run(id)
);
```

操作类型：

```text
edit_event
mark_key
mark_risk
ignore_event
link_topic
unlink_topic
merge_event
split_event
re_extract
re_cluster
sync_graph
```

---

## 11.14 graph_sync_outbox

```sql
CREATE TABLE IF NOT EXISTS graph_sync_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aggregate_type TEXT NOT NULL,
    aggregate_id INTEGER NOT NULL,
    operation TEXT NOT NULL,
    projection_version INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload TEXT,
    status TEXT DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    next_retry_at TEXT,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    CHECK (status IN ('pending', 'running', 'succeeded', 'failed'))
);

CREATE TABLE IF NOT EXISTS graph_projection_state (
    aggregate_type TEXT NOT NULL,
    aggregate_id INTEGER NOT NULL,
    projection_version INTEGER NOT NULL,
    sync_status TEXT NOT NULL DEFAULT 'pending',
    synced_at TEXT,
    error_message TEXT,
    PRIMARY KEY(aggregate_type, aggregate_id),
    CHECK (sync_status IN ('pending', 'synced', 'failed'))
);
```

---

## 11.15 llm_provider_config

如果项目已有 LLM 配置表或配置文件，应优先复用或迁移，不强制新建。

没有现成结构时，可使用：

```sql
CREATE TABLE IF NOT EXISTS llm_provider_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    base_url TEXT NOT NULL,
    api_key_encrypted TEXT,
    chat_model TEXT,
    embedding_model TEXT,
    temperature REAL DEFAULT 0.2,
    max_tokens INTEGER DEFAULT 4096,
    timeout_seconds INTEGER DEFAULT 60,
    enabled INTEGER DEFAULT 1,
    remark TEXT,
    last_test_status TEXT,
    last_test_message TEXT,
    last_test_time TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);
```

`provider_type`：

```text
openai_compatible
ollama
custom
```

---

## 11.16 llm_task_config

```sql
CREATE TABLE IF NOT EXISTS llm_task_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL UNIQUE,
    provider_config_id INTEGER NOT NULL,
    model_name TEXT NOT NULL,
    temperature REAL,
    max_tokens INTEGER,
    timeout_seconds INTEGER,
    enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY(provider_config_id) REFERENCES llm_provider_config(id)
);
```

任务类型：

```text
event_extraction
topic_summary
relation_judgement
risk_detection
lifecycle_stage_judgement
embedding
```

---

## 11.17 llm_call_log

```sql
CREATE TABLE IF NOT EXISTS llm_call_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL,
    analysis_run_id INTEGER,
    task_type TEXT,
    provider_config_id INTEGER,
    model_name TEXT,
    prompt_version TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    latency_ms INTEGER,
    success INTEGER,
    error_code TEXT,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(analysis_run_id) REFERENCES analysis_run(id)
);
```

默认不要保存完整 prompt，避免数据库膨胀和敏感信息泄露。

---

## 11.18 analysis_run

每次自动分析或人工触发的重新分析都创建独立批次，避免覆盖历史结果后无法追溯。

```sql
CREATE TABLE IF NOT EXISTS analysis_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_type TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    prompt_version TEXT,
    score_version TEXT DEFAULT 'v1',
    trace_id TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    completed_at TEXT,
    CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled'))
);
```

---

## 11.19 processing_job

```sql
CREATE TABLE IF NOT EXISTS processing_job (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_id INTEGER NOT NULL,
    analysis_run_id INTEGER,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    lease_expires_at TEXT,
    next_retry_at TEXT,
    error_code TEXT,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY(analysis_run_id) REFERENCES analysis_run(id),
    CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled'))
);

CREATE TABLE IF NOT EXISTS processing_job_attempt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    processing_job_id INTEGER NOT NULL,
    attempt_no INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    success INTEGER,
    error_code TEXT,
    error_message TEXT,
    FOREIGN KEY(processing_job_id) REFERENCES processing_job(id),
    UNIQUE(processing_job_id, attempt_no)
);
```

---

## 11.20 人工修订与重复事件候选

人工修订采用字段级覆盖，后续自动分析只能更新未锁定字段：

```sql
CREATE TABLE IF NOT EXISTS event_field_override (
    event_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    override_value TEXT,
    operator TEXT DEFAULT 'local_user',
    reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    PRIMARY KEY(event_id, field_name),
    FOREIGN KEY(event_id) REFERENCES event(id)
);

CREATE TABLE IF NOT EXISTS duplicate_event_candidate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_event_id INTEGER NOT NULL,
    candidate_event_id INTEGER NOT NULL,
    same_event_score REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    analysis_run_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY(source_event_id) REFERENCES event(id),
    FOREIGN KEY(candidate_event_id) REFERENCES event(id),
    FOREIGN KEY(analysis_run_id) REFERENCES analysis_run(id),
    UNIQUE(source_event_id, candidate_event_id),
    CHECK (source_event_id <> candidate_event_id),
    CHECK (status IN ('pending', 'confirmed', 'rejected'))
);
```

确认合并后设置 `event.canonical_event_id`。原事件继续保留，人工可以撤销归并。

---

## 11.21 sqlite-vec 与 Embedding

sqlite-vec 的加载方式和虚拟表语法需要在阶段 0 根据 Windows + Python 3.12 环境验证。概念模型如下：

```text
raw_document_embedding：
  raw_document_id
  embedding_model
  embedding_dimension
  content_hash
  vector

event_embedding：
  event_id
  embedding_model
  embedding_dimension
  content_hash
  vector
```

向量记录必须带模型名称、维度和内容哈希。模型切换或正文变化后重新生成，不允许混用不同模型或不同维度的向量。

---

## 11.22 Schema 版本、外键与索引

所有连接必须开启：

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
```

数据库必须提供显式 migration，不允许只依赖 Repository 初始化时零散执行 `CREATE TABLE IF NOT EXISTS`。

```sql
CREATE TABLE IF NOT EXISTS schema_migration (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

首批索引至少覆盖：

```sql
CREATE INDEX IF NOT EXISTS idx_raw_document_publish_time
ON raw_document(publish_time);

CREATE INDEX IF NOT EXISTS idx_event_event_time_status
ON event(event_time, process_status);

CREATE INDEX IF NOT EXISTS idx_event_source_raw_document
ON event_source(raw_document_id);

CREATE INDEX IF NOT EXISTS idx_topic_event_event
ON topic_event(event_id);

CREATE INDEX IF NOT EXISTS idx_event_relation_source
ON event_relation(source_event_id, relation_type);

CREATE INDEX IF NOT EXISTS idx_event_relation_target
ON event_relation(target_event_id, relation_type);

CREATE INDEX IF NOT EXISTS idx_processing_job_status_retry
ON processing_job(status, next_retry_at);

CREATE INDEX IF NOT EXISTS idx_graph_sync_outbox_status_retry
ON graph_sync_outbox(status, next_retry_at);
```

---

# 12. Neo4j 图谱模型

## 12.1 节点

```cypher
(:Event {
  id,
  title,
  event_type,
  event_time,
  importance_score,
  confidence_score
})

(:Topic {
  id,
  name,
  lifecycle_stage,
  heat_score,
  momentum_score
})

(:Entity {
  id,
  name,
  entity_type
})
```

后续可扩展：

```cypher
(:Stock)
(:Industry)
(:Concept)
(:Commodity)
(:Source)
```

---

## 12.2 关系

```cypher
(:Event)-[:BELONGS_TO {relevance_score, role_in_topic}]->(:Topic)

(:Event)-[:MENTIONS {role, relevance_score}]->(:Entity)

(:Event)-[:CAUSES {strength_score, confidence_score}]->(:Event)

(:Event)-[:SUPPORTS {strength_score, confidence_score}]->(:Event)

(:Event)-[:CONTRADICTS {strength_score, confidence_score}]->(:Event)

(:Event)-[:FOLLOW_UP {strength_score, confidence_score}]->(:Event)

(:Event)-[:SAME_TOPIC {strength_score, confidence_score}]->(:Event)

(:Entity)-[:SUPPLY_CHAIN {relation_summary, confidence_score}]->(:Entity)
```

`SAME_TOPIC` 默认由 SQLite `topic_event` 推导；仅在人工确认或性能验证确有必要时持久化。产业链关系属于实体知识，优先表达为 `Entity -> Entity`，不直接混入事件因果链。

---

## 12.3 约束

```cypher
CREATE CONSTRAINT event_id_unique IF NOT EXISTS
FOR (e:Event) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT topic_id_unique IF NOT EXISTS
FOR (t:Topic) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;
```

Neo4j 必须支持从 SQLite 全量重建。图谱查询失败时返回可识别的降级状态，不影响 SQLite 页面继续使用。

---

# 13. 大模型抽取设计

## 13.1 事件抽取 JSON

```json
{
  "events": [
    {
      "title": "存储芯片价格进入上行周期",
      "summary": "多家存储原厂上调 DRAM 和 NAND 报价，市场预期行业供需格局改善。",
      "event_type": "price_change",
      "event_time": "2026-05-28",
      "sentiment": "positive",
      "impact_direction": "benefit",
      "entities": [
        {
          "name": "DRAM",
          "type": "product",
          "role": "affected_product"
        },
        {
          "name": "三星电子",
          "type": "company",
          "role": "supplier"
        }
      ],
      "industries": ["半导体", "存储芯片"],
      "concepts": ["HBM", "AI服务器", "存储周期"],
      "related_assets": [],
      "evidence": [
        {
          "text": "多家存储原厂近期上调 DRAM 报价。",
          "evidence_level": "B",
          "paragraph_index": 12,
          "start_offset": 0,
          "end_offset": 18
        }
      ],
      "importance_score": 0.78,
      "novelty_score": 0.64,
      "market_relevance_score": 0.82,
      "confidence_score": 0.81
    }
  ]
}
```

---

## 13.2 关系判断 JSON

```json
{
  "is_related": true,
  "relation_type": "support",
  "relation_summary": "事件 B 进一步验证了事件 A 中提到的存储供需改善趋势。",
  "strength_score": 0.76,
  "confidence_score": 0.72,
  "evidence_refs": [101, 205]
}
```

大模型不得直接凭空生成关系。候选关系必须先由规则、实体重合、时间窗口、向量相似度等方式召回。关系结论必须绑定已有 `evidence` 记录，不接受无法回溯到原始材料的自由文本证据。

---

# 14. 事件去重与聚类

## 14.1 文档去重

依据：

```text
source_url
content_hash
title similarity
```

规则：

```text
source_url 相同，认为重复。
content_hash 相同，认为重复。
标题高度相似且发布时间接近，标记为疑似重复。
```

---

## 14.2 事件去重

依据：

```text
事件标题相似度
摘要向量相似度
实体重合度
事件时间接近度
事件类型一致性
来源数量
```

评分：

```text
same_event_score =
0.30 * title_similarity
+ 0.30 * embedding_similarity
+ 0.20 * entity_overlap
+ 0.10 * time_proximity
+ 0.10 * event_type_match
```

如果：

```text
same_event_score >= 0.85
```

则生成重复事件候选，等待规则确认或人工确认。确认后设置 `canonical_event_id`，保留原事件和操作日志，不执行破坏性删除。

---

## 14.3 主题聚类

主题归并依据：

```text
事件语义相似度
共同实体
共同概念
共同产业链
共同市场资产
时间连续性
事件关系密度
```

第一阶段允许人工确认主题归属。

---

## 14.4 去重与聚类版本化

每次自动判断必须记录：

```text
analysis_run_id
algorithm_version
embedding_model
score_version
threshold
```

阈值调整后允许重新计算候选，不得静默覆盖人工确认结果。

---

# 15. 评分模型

## 15.1 事件重要性评分

```text
importance_score =
0.25 * source_authority_score
+ 0.20 * entity_importance_score
+ 0.20 * market_relevance_score
+ 0.15 * novelty_score
+ 0.10 * evidence_strength_score
+ 0.10 * relation_centrality_score
```

所有评分项必须归一化到 `[0, 1]`，并记录 `score_version`。第一阶段使用 `v1` 固定权重，调整权重时生成新版本，不覆盖历史分析批次。

---

## 15.2 主题热度评分

```text
heat_score =
近7天事件数量
+ 多来源覆盖程度
+ 相关实体数量
+ 高重要性事件数量
+ 图谱关系密度
```

主题热度按滚动 7 天窗口计算，各分量归一化到 `[0, 1]` 后再加权汇总。

---

## 15.3 早期信号评分

```text
early_signal_score =
新颖度
+ 高质量低传播证据
+ 多个弱信号交叉验证
+ 与成熟主题存在产业链关联
+ 尚未明显进入市场共识
```

早期信号评分同样记录 `score_version` 和计算时间窗口。

---

# 16. API 设计

前端接口优先沿用当前项目 `/api/frontend/modules/*` 风格。新增事件洞察使用独立前缀：

```text
/api/frontend/modules/event-insight/*
```

现有未来事件静态日历继续使用：

```text
/api/frontend/modules/event-outlook
/api/frontend/modules/event-outlook/events
/api/frontend/modules/event-outlook/events/{event_id}
```

新增事件洞察不得修改现有静态日历接口契约。

## 16.1 事件列表

```http
GET /api/frontend/modules/event-insight/events
```

参数：

```text
startDate
endDate
materialType
eventType
processStatus
keyword
entity
topicId
minImportance
minConfidence
page
pageSize
sortBy
sortOrder
```

成功响应：

```json
{
  "items": [],
  "page": 1,
  "pageSize": 20,
  "total": 0,
  "traceId": "trace-id"
}
```

---

```http
GET /api/frontend/modules/event-insight/events/{eventId}
```

---

```http
PUT /api/frontend/modules/event-insight/events/{eventId}
```

---

```http
POST /api/frontend/modules/event-insight/events/{eventId}/ignore
```

请求：

```json
{
  "reason": "重复新闻或低价值噪声"
}
```

---

```http
POST /api/frontend/modules/event-insight/topics
```

请求：

```json
{
  "name": "内存涨价",
  "summary": "围绕存储芯片供需和价格变化建立研究主题。"
}
```

---

```http
POST /api/frontend/modules/event-insight/events/{eventId}/link-topic
```

请求：

```json
{
  "topicId": 1,
  "roleInTopic": "supporting_event"
}
```

---

```http
POST /api/frontend/modules/event-insight/events/batch-action
```

请求：

```json
{
  "eventIds": [1, 2, 3],
  "action": "link_topic",
  "params": {
    "topicId": 1,
    "roleInTopic": "supporting_event"
  }
}
```

批量操作必须逐项返回结果，不得因单条失败吞掉其他成功项：

```json
{
  "succeededEventIds": [1, 2],
  "failedItems": [
    {
      "eventId": 3,
      "error": "event_not_found"
    }
  ],
  "traceId": "trace-id"
}
```

---

## 16.2 主题溯源

```http
GET /api/frontend/modules/event-insight/topics/trace
```

参数：

```text
keyword
startDate
endDate
eventTypes
sourceTypes
minConfidence
```

返回：

```json
{
  "topic": {},
  "summary": {},
  "timeline": [],
  "earlySignals": [],
  "keyCatalysts": [],
  "marketConfirmations": [],
  "risks": [],
  "evidences": []
}
```

---

```http
POST /api/frontend/modules/event-insight/topics/analyze
```

请求：

```json
{
  "keyword": "内存涨价",
  "startDate": "2025-01-01",
  "endDate": "2026-06-02"
}
```

成功：`202`

```json
{
  "jobId": 1001,
  "analysisRunId": 2001,
  "status": "pending",
  "traceId": "trace-id"
}
```

---

```http
PUT /api/frontend/modules/event-insight/topics/{topicId}/events/{eventId}
```

请求：

```json
{
  "roleInTopic": "key_catalyst",
  "relevanceScore": 0.9
}
```

---

```http
POST /api/frontend/modules/event-insight/topics/{topicId}/events/{eventId}/unlink
```

从主题中移除事件时保留操作日志。

---

## 16.3 事件关系图

```http
GET /api/frontend/modules/event-insight/graph/topic/{topicId}
```

参数：

```text
startDate
endDate
relationTypes
eventTypes
minConfidence
depth
```

返回：

```json
{
  "nodes": [],
  "edges": []
}
```

---

```http
GET /api/frontend/modules/event-insight/relations/{relationId}
```

---

```http
POST /api/frontend/modules/event-insight/relations
```

请求：

```json
{
  "sourceEventId": 1,
  "targetEventId": 2,
  "relationType": "support",
  "relationSummary": "后续报价数据验证了供需改善。",
  "strengthScore": 0.8,
  "evidenceIds": [101, 205]
}
```

---

```http
PUT /api/frontend/modules/event-insight/relations/{relationId}
```

---

```http
POST /api/frontend/modules/event-insight/relations/{relationId}/archive
```

归档关系时保留关系证据和操作日志，不物理删除。

---

```http
GET /api/frontend/modules/event-insight/graph/path
```

参数：

```text
startEventId
endEventId
maxDepth
```

`maxDepth` 第一阶段限制为 `1..5`。只允许遍历 `CAUSES | SUPPORTS | CONTRADICTS | FOLLOW_UP`，必须限制主题范围并避免环路。

---

## 16.4 大模型配置

```http
GET /api/system/llm/providers
```

```http
POST /api/system/llm/providers
```

```http
PUT /api/system/llm/providers/{id}
```

```http
POST /api/system/llm/providers/{id}/disable
```

禁用语义：

```text
如果 Provider 仍被 llm_task_config 引用，返回 409 provider_in_use。
解除任务映射后允许禁用，并从新建任务的可选列表中隐藏。
历史 llm_call_log 和既有分析批次保留。
```

```http
POST /api/system/llm/providers/{id}/test
```

```http
GET /api/system/llm/task-configs
```

```http
PUT /api/system/llm/task-configs/{taskType}
```

---

## 16.5 导入与任务状态

```http
POST /api/frontend/modules/event-insight/documents/import
```

支持 URL、纯文本或受控文件上传。成功返回 `202 + jobId`。

```http
GET /api/frontend/modules/event-insight/jobs/{jobId}
```

成功响应：

```json
{
  "id": 1001,
  "jobType": "extract_event",
  "status": "running",
  "attemptCount": 1,
  "maxAttempts": 3,
  "error": null,
  "traceId": "trace-id"
}
```

---

## 16.6 错误、幂等与可观测性

统一错误响应：

```json
{
  "error": "machine_readable_error_code",
  "message": "面向用户的简洁说明",
  "traceId": "trace-id"
}
```

要求：

```text
1. 可重试写接口支持 Idempotency-Key 请求头。
2. Controller 只做参数校验和响应转换，业务逻辑进入 Service，SQL 进入 Repository。
3. 日志包含 traceId、jobId、analysisRunId 和必要的业务主键。
4. 日志禁止输出 API Key、完整请求头和完整 prompt。
5. 400 表示输入错误，404 表示资源不存在，409 表示状态冲突，202 表示异步任务已受理，503 表示依赖不可用。
```

---

# 17. 前端组件建议

组件命名仅为建议，应按当前项目命名风格调整。

## 17.1 事件列表页

```text
EventListPage
EventFilterBar
EventTable
EventDetailDrawer
EventBatchActionBar
EventEditDialog
TopicLinkDialog
```

---

## 17.2 主题溯源页

```text
TopicTracePage
TopicSearchBar
TopicSummaryCard
LifecycleStageBadge
EventTimeline
EvidenceList
RiskPanel
EventDetailDrawer
ManualEditDialog
```

---

## 17.3 事件关系图页

```text
EventGraphPage
GraphToolbar
EventGraphCanvas
NodeDetailDrawer
EdgeDetailDrawer
PathTracePanel
GraphFilterPanel
RelationEditDialog
```

---

## 17.4 大模型配置页

```text
LlmSettingsPage
LlmProviderTable
LlmProviderEditDialog
LlmTaskMappingTable
LlmConnectionTestButton
LlmCallLogPanel
```

---

# 18. 人工校正设计

第一阶段必须支持人工校正。

## 18.1 事件校正

支持：

```text
编辑标题
编辑摘要
编辑事件时间
编辑事件类型
编辑评分
标记关键节点
标记早期信号
标记市场确认
标记风险事件
合并事件
删除事件
忽略事件
```

“删除事件”在第一阶段统一实现为归档软删除，设置 `archived_at` 并记录操作日志，不物理删除历史事实。

---

## 18.2 关系校正

支持：

```text
新增关系
删除关系
修改关系类型
修改关系强度
确认关系
取消确认
添加备注
```

---

## 18.3 校正优先级

人工校正优先于模型生成。

相关数据：

```text
event_field_override：事件字段级人工覆盖
manual_confirmed：人工确认关系
event_operation_log：修订前后值、原因和操作人
```

“删除关系”在第一阶段统一实现为归档软删除，设置 `archived_at` 并保留关系证据和操作日志。

当人工确认后，后续自动分析不得直接覆盖人工结果。自动分析仍可更新未锁定字段，并创建新的 `analysis_run` 保留历史。

---

# 19. 开发阶段规划

## 阶段 0：技术验证与边界确认

目标：

```text
确认现有未来事件静态日历的页面、API 和 timeline_events 表保持不变
验证 Windows + Python 3.12 环境加载 sqlite-vec
验证 FTS5 unicode61 对中文标题和正文的召回效果
验证 Neo4j Community 本地启动、约束创建、全量重建和不可用降级
对候选前端图库进行小规模性能验证
确认现有 BaseLLMProvider 和 ArkResearchProvider 的统一迁移路径
```

验收：

```text
形成可执行验证记录
明确 sqlite-vec 加载方式和虚拟表 DDL
明确中文检索实现方案
明确图谱组件选择
确认静态日历回归测试继续通过
```

---

## 阶段 1：代码调研与页面骨架

目标：

```text
调研当前项目页面结构、导航结构、样式体系
调研历史 LLM 接入方法
Event Outlook 下新增事件列表、主题溯源、事件关系图入口
System Settings 下新增大模型配置入口
完成页面骨架和 mock 数据展示
```

验收：

```text
新增页面均可打开
页面风格与当前项目一致
不影响国内/国际页面
国内/国际页面继续使用现有静态日历 API 和 timeline_events 表
不重复新建已有 LLM 能力
```

---

## 阶段 2：大模型配置能力

目标：

```text
复用或适配已有 LLM 接入方法
实现模型供应商配置
实现任务模型映射
实现连接测试
实现 API Key 加密/脱敏
实现调用日志
```

验收：

```text
可以配置 OpenAI Compatible API
可以测试连接
事件抽取服务可以通过 task_type 调用模型
API Key 不明文展示、不输出到日志
```

---

## 阶段 3：事件列表基础能力

目标：

```text
raw_document 入库
event 入库
事件列表查询
事件详情抽屉
事件编辑
事件忽略
事件归入主题
批量操作
processing_job 入库和任务状态查询
```

验收：

```text
可以展示每天扫描/导入的事件
可以查看事件详情和证据
可以人工整理事件
```

---

## 阶段 4：事件抽取与证据链

目标：

```text
原始材料 → 大模型事件抽取
事件 JSON Schema 校验
实体入库
证据链入库
FTS5 索引
analysis_run 追溯
```

验收：

```text
输入一篇财经新闻/公告/研报摘要，可以抽取结构化事件
事件列表页可查看抽取结果和证据链
```

---

## 阶段 5：向量检索与聚类

目标：

```text
接入 sqlite-vec
生成事件 embedding
实现相似事件召回
实现重复事件候选和人工确认归并
实现主题聚类
```

验收：

```text
多篇相似新闻不会重复生成大量孤立事件
相似事件可以归并为同一主题节点
```

---

## 阶段 6：主题溯源页

目标：

```text
主题检索
主题摘要
事件时间线
早期信号
关键催化
市场确认
风险反证
证据链
人工校正
```

验收：

```text
输入“内存涨价”，能生成完整事件发酵时间线
能区分早期信号、关键催化、市场确认、风险事件
所有结论可追溯到证据来源
```

---

## 阶段 7：事件关系图页

目标：

```text
事件关系生成
Neo4j 同步
Neo4j 降级
从 SQLite 全量重建图谱投影
主题子图查询
节点详情
边详情
路径追踪
关系人工修正
```

验收：

```text
事件关系图页展示真实 Neo4j 数据
支持节点点击、边点击、路径查询
支持人工调整关系
```

---

# 20. Codex 实现要求

Codex 实现时必须遵守：

```text
1. 先调研当前项目结构，再实施新增页面。
2. 新增页面必须适配当前项目已有风格，不要写死全新的 UI 体系。
3. 不要破坏现有 Event Outlook 国内/国际页面。
4. 现有国内/国际页面是未来事件静态日历，继续使用现有 timeline_events、EventsOutlookService、EventsOutlookStore 和 /api/frontend/modules/event-outlook 契约。
5. 新增事件洞察是独立研究域，不得复用静态日历表或把洞察工作区 Tab 传给静态日历 region。
6. Event Outlook 下新增“事件列表”“主题溯源”“事件关系图”。
7. System -> Settings 下新增“大模型配置”页面或 Tab。
8. 项目中已有 BaseLLMProvider 和 ArkResearchProvider，必须按迁移顺序复用或适配，不要重复造轮子。
9. 如已有通用 API 客户端、配置加密、Settings 表单组件，应优先复用。
10. SQLite 是事实主库，Neo4j 是关系投影库。
11. 事件抽取、主题摘要、关系判断等模型调用必须通过统一 LLM 调用层。
12. Prompt 必须集中管理，不要散落在业务代码中。
13. API Key 必须加密保存、脱敏展示，日志不得输出明文。
14. 大模型调用失败必须记录日志，并允许重试。
15. 所有核心分析结果必须保留可定位 evidence。
16. 大模型输出必须经过 JSON Schema 校验。
17. 人工校正结果优先于自动分析结果，使用字段级覆盖并记录修订日志。
18. 耗时任务必须异步执行，支持幂等、重试、恢复和状态查询。
19. 先实现 mock 数据页面，再逐步接入真实 API。
20. 数据库变更必须提供 migration，SQLite 连接必须开启 foreign_keys 和 WAL。
21. 不引入 Kafka、Redis、ES、MinIO 等额外组件。
22. 新增接口、字段和行为变化必须同步更新 docs/api-contract.md、docs/architecture.md、docs/test-strategy.md 和 CHANGELOG.md。
```

---

# 21. 测试与回归矩阵

## 21.1 后端 Repository

```text
静态日历 timeline_events 回归
migration 可重复执行
foreign_keys 生效
FTS5 插入、更新、删除触发器同步
中文标题和正文召回
证据片段原文定位
任务原子领取、租约恢复、幂等和重试
字段级人工覆盖不会被自动分析覆盖
重复事件候选确认和撤销
outbox 幂等消费与失败重试
```

## 21.2 后端 Service 与 API

```text
现有 /api/frontend/modules/event-outlook 契约不变
事件列表筛选、排序和分页
导入接口返回 202 + jobId
主题重新分析返回 202 + analysisRunId
批量操作部分成功响应
LLM 超时、限流、非 JSON 和 Schema 校验失败
Provider 被任务映射引用时禁用返回 409
Neo4j 不可用时列表和主题时间线仍可用
图谱全量重建后投影一致
错误响应包含 error、message 和 traceId
```

## 21.3 前端

```text
国内 / 国际继续渲染未来事件静态日历
events / topic-trace / event-graph 不向静态日历接口发送非法 region
事件列表加载、筛选、分页、批量操作和详情抽屉
任务状态轮询、失败提示和重新触发
证据链展开后可回到原始材料位置
Neo4j 降级提示
大模型配置脱敏展示和连接测试
所有展示时间使用浏览器本地时区
```

## 21.4 发布门禁

```text
后端 pytest 全量通过
前端 Vitest 全量通过
前端 npm run build 通过
静态日历现有回归通过
使用固定测试材料跑通：导入 → 抽取 → 证据 → 主题 → 关系 → 图谱投影
关闭 Neo4j 后验证降级页面
```

---

# 22. 第一阶段最终交付物

第一阶段完成后，系统应具备：

```text
Event Outlook 下新增：
  - 事件列表
  - 主题溯源
  - 事件关系图

System Settings 下新增：
  - 大模型配置
```

事件列表页支持：

```text
查看每日扫描/导入事件
筛选事件
查看事件详情
查看证据链
编辑事件
忽略事件
归入主题
批量操作
重新抽取
同步图谱
```

主题溯源页支持：

```text
输入主题
选择时间范围
查看主题摘要
查看发酵阶段
查看事件时间线
查看早期信号
查看关键催化
查看市场确认
查看风险反证
查看证据链
人工校正事件
```

事件关系图页支持：

```text
按主题展示事件图谱
按时间/类型/关系过滤
点击节点查看事件详情
点击边查看关系详情
查看证据链
查询事件路径
人工调整关系
```

大模型配置页支持：

```text
配置模型供应商
配置 Base URL
配置 API Key
配置 Chat Model
配置 Embedding Model
配置任务模型映射
测试连接
查看调用状态
记录调用日志
```

---

# 23. 总结

本次新增的事件洞察模块不是简单的信息展示页，而是 TrendInsight 投资研究能力的重要入口。

现有国内 / 国际未来事件静态日历继续承担“将要发生什么”的观察职责。新增事件洞察独立承担“已经出现了哪些证据、主题如何发酵”的研究职责。

第一阶段目标是：

```text
用有限页面实现完整研究闭环。
```

具体来说：

```text
事件列表页负责承接每日扫描与事件整理；
主题溯源页负责还原事件如何发酵；
事件关系图页负责展示事件如何连接；
大模型配置页负责提供事件抽取和分析能力；
SQLite 负责保存事实；
FTS5 负责全文证据检索；
sqlite-vec 负责语义召回；
Neo4j 负责图谱关系和路径分析；
大模型负责抽取、归纳和关系判断；
人工校正负责保证研究质量。
```

最终模块应服务于一个核心问题：

```text
市场热点不是突然出现的。
它在爆发前一定留下过痕迹。
本模块的价值，就是把这些痕迹系统性地捕获、整理、连接和验证。
```
