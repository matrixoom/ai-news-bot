# 变更记录（Changelog）

本项目遵循“按时间倒序记录”的方式维护变更日志。建议参考 Keep a Changelog 思路，结合本仓库实际调整。

## [Unreleased]

### Added

- System Settings 新增独立 RSS 源配置 Tab：首次展示 `fetcher.py` 原有默认 RSS 源，支持新增/更新/删除和手动抓取，并将 RSS 条目接入 Event Insight 事件列表。
- System LLM Settings 新增连接测试调用日志接口：连接测试会发起真实 OpenAI-compatible 调用并写入脱敏 `llm_call_log`，前端支持编辑和禁用 provider。
- Event Insight 事件列表、主题溯源和关系图补齐主要按钮交互：材料导入、事件编辑、批量处理、新建主题、新增关系和保存视图均绑定真实 API 或可见状态反馈。
- Event Insight 新增 `POST /api/frontend/modules/event-insight/relations`，支持人工新增事件关系并更新关系图 SQLite 投影。
- Event Insight 新增 P10 发布硬化：新增 `GET /api/frontend/modules/event-insight/topics` 主题列表接口，主题溯源页和事件关系图页改为先读取可选主题，移除固定 `topicId=1` 假设。
- Event Insight 新增 P9 事件关系图 SQLite 投影：`GET /api/frontend/modules/event-insight/graph` 返回真实事件节点和 `event_relation` 关系边，前端关系图从 mock 切换为 API 加载并支持节点详情。
- Event Insight 新增 P8 主题溯源真实数据链路：`GET /api/frontend/modules/event-insight/topics/{topicId}/trace` 返回主题、指标、阶段、时间线和证据摘要，前端主题溯源页从 mock 切换为 API 加载。
- Event Insight 新增 P7 检索、重复候选与规则聚类服务：中文 n-gram fallback 召回 active 事件，重复候选仅写入 `duplicate_event_candidate`，规则聚类仅关联 `topic_event`，并提供 sqlite-vec 可选探测能力。
- Event Insight 新增 P6 事件抽取服务：通过 `LlmTaskRouter` 将原始材料抽取为事件、证据和实体，证据片段必须能在原文中定位，并在事件详情中展示证据原文位置。
- System Settings 新增真实 LLM Runtime 配置：支持 OpenAI-compatible provider 的加密持久化、脱敏列表、连接测试、任务模型映射和 `LlmTaskRouter`，ArkResearchProvider 改为复用统一 provider factory。
- Event Insight 新增事件工作台真实 API 与前端联调：支持事件列表/详情、人工字段覆盖、忽略、主题创建、事件关联主题和批量操作，并将前端事件列表从 Mock 数据切换到 `/api/frontend/modules/event-insight/events`。
- Event Insight 新增材料导入与本地任务队列接口，支持 text/url/受控 JSON file 导入、`parse_document` 任务创建、任务状态查询、幂等键、租约恢复、attempt 日志和路径穿越校验。
- Event Insight 新增独立 `.data/event_insight.db` SQLite 事实库、`001_event_insight_core` migration、Repository 基础写读能力和数据层回归测试，覆盖 FTS 同步、外键、人工覆盖、重复候选与 graph outbox 幂等。
- Event Insight 完成 P0 技术验证记录，明确 sqlite-vec 可加载、FTS5 中文召回需要 n-gram 辅助、Neo4j 必须可选降级、关系图首版优先复用 ECharts，并补充后续检索与图谱测试 fixture。
- Event Outlook 新增 `事件列表 / 主题溯源 / 事件关系图` 三个 Mock 研究工作台，Settings 新增展示型大模型配置页；本阶段先交付可浏览前端效果，静态日历保持原有行为，真实数据链路将在后续增量接入。
- Push Center `Schedules` 页面改为全宽日报预览，计划任务与投递配置收纳到齿轮设置弹窗；预览页使用 Heroicons 图标提供设置、全量刷新、刷新预览和立即发送操作。
- Push preview 宽基指数图表新增 `3个月 / 6个月 / 1年 / 2年 / 3年` 时间范围，默认推送近 `1年`；切换范围会使用本地历史重绘，全量刷新按当前范围拉取并仅按日期 `upsert`，保留 SQLite 中既有历史。
- Macro Data 就业指标 `中国社会保险基金支出:失业保险:累计值` 补入 2005-2024 年共 20 个年度官方整理点位，旧样例库会在启动时替换为该序列。
- Macro Data 就业指标 2024 年点位按人社部统计公报口径规范为 `1842` 亿元，财政部 `1842.21` 亿元决算数保留为交叉校验来源。
- Macro Data 新增 `就业` 子标签页，注册 `中国社会保险基金支出:失业保险:累计值` 年度折线图，并为该指标创建独立 SQLite 事实表。
- 新增与 Macro Data 平级的 Event Outlook 一级目录页，提供国内/国际子标签、自绘横向时间轴、画布内日期范围筛选、弹窗手工录入和编辑事件能力。
- Event Outlook 新增科技、时政、财经三类未来一年事件，三类在时间轴中分别用不同颜色展示；事件持久化到 `.data/events_outlook.db` 的 `timeline_events` 表。
- 新增 Notes 一级目录页，当前作为空白工作区入口预留。
- 新增 Event Outlook 前端接口：`/api/frontend/modules/event-outlook`、`/api/frontend/modules/event-outlook/events` 与 `/api/frontend/modules/event-outlook/events/{event_id}`。
- Macro Data 景气标签新增 `综合PMI` 指标，随制造业/非制造业 PMI 一起注册、同步并以同样的折线图样式展示。
- Macro Data 信贷标签在 `新增人民币贷款` 下方新增 `居民活期存款` 宽图表，复用“总量虚线 + 分项堆叠柱 + 同名虚线折线”格式，并新增居民存款总计、活期、定期及其他三张事实表。
- 新增与 Push Center 平级的 Macro Data 模块，提供 `GDP / 信贷 / 杠杆率 / 物价` 子标签页、ECharts 图表、预设时间跨度和自定义日期范围。
- 新增 Macro Data 后端接口：`/api/frontend/modules/macro-data` 与 `/api/frontend/modules/macro-data/charts/{chart_id}`。
- 新增 `.data/macro_data.db` 本地 SQLite 持久化，8 个宏观指标各自一张事实表，并提供注册表与同步状态表。
- GDP 子标签新增 `GDP增速` 组合图，基于名义 GDP 与实际 GDP 总量表派生同比增速，并在同一图中展示两条序列。
- 新增 `main.py macro-sync` 宏观数据同步命令，回填 GDP 历史数据到本地 SQLite，并新增名义/实际 GDP 增速持久化表。
- Macro Data 图表时间范围新增 `15年 / 20年 / 25年 / 30年`，并将 `一年 / 三年` 展示文案调整为 `1年 / 3年`。
- GDP 图表新增 `季度 / 年度` 数据频率切换；SQLite 事实表幂等键调整为 `(period_end, frequency)`，避免年度数据与四季度数据在 `YYYY-12-31` 相互覆盖。
- GDP 同步口径调整为季度展示当季值、年度展示全年值，完整四季度合计会覆盖同年年度值，确保年度值与四个季度之和一致。
- 新增 `AGENTS.md`，统一 Codex/代理协作与变更规则。
- 新增 `docs/architecture.md`，明确架构分层与模块边界。
- 新增 `docs/api-contract.md`，固化前后端接口契约与错误语义。
- 新增 `docs/test-strategy.md`，固化测试分层与回归门禁。

### Changed

- System Settings 的 LLM provider 连接测试改为真实调用 OpenAI-compatible 模型，并在前端区分测试中、成功和失败状态，失败详情会脱敏展示。
- 推送中心宽基指数全量刷新不再只做按日期 `upsert`：完整历史帧会事务性替换最近 92 天窗口，短序列或空结果则保留上次可用历史并在进度弹窗中提示，避免旧脏点残留或上游异常清空图表。国内宽基指数历史改为优先使用响应更稳定的新浪日线，东方财富保留为回退源。
- 修复 Market Data 全球期货历史把最高价误当收盘价的问题；布伦特、黄金、白银、铜在东方财富历史端点异常时会回退到新浪外盘日线。单图手动刷新不再触发同分类其他指标，空结果也不会覆盖已有 SQLite 历史。
- 推送中心宽基指数刷新在周末不再尝试拼接盘中报价，避免非交易日出现误导性的快照校验日志。
- Event Outlook 时间轴改为单画布布局，事件通过上下连线挂载到主时间轴；同一日期的多个事件按紧凑层级堆叠，并使用清新淡色系区分科技、时政、财经分类。
- Event Outlook 页面移除外层模块标题卡片，仅保留时间轴画布；画布支持鼠标框选缩放和滚轮按指针位置缩放。
- Pytest 默认收集范围限定为 `tests/`，避免继续递归执行已归档到 `to_delete/tests/` 的历史用例。
- Macro Data 的 `新增人民币贷款` 与 `居民活期存款` 组合柱线图 tooltip 按业务序列名去重，避免同名柱状图与折线图在悬浮框中重复展示同一数值。
- 推送中心市场日报组合图下方柱体改为每日成交量，表格中的收盘、MA20 与乖离率字段保持不变；市场历史库新增可选 `volume` 字段并兼容旧 SQLite 数据。
- Market Data 全国 70 城二手房价格指数城市选择器支持点击外部区域自动确认并关闭，确认/取消操作移动到搜索框右侧的 Heroicons 小图标；同一城市的全局、同比、环比折线统一颜色并用线型区分指标。
- 综合 PMI 本地库已补齐 AkShare 真实月度数据，指标注册状态在真实同步后不再被默认样例种子回写为 `sample`。
- Macro Data 信贷标签的 `新增人民币贷款` 从多折线图改为“总量虚线 + 居民/企业短期与长期贷款堆叠柱 + 同名虚线折线”，并修复人民银行 Excel 10 月列被解析成 1 月导致细分贷款缺 10-11 月数据的问题。
- Macro Data 历史同步新增居民存款余额解析，优先读取人民银行 2000 年以来归档 HTML 与 2015 年以来年度 Excel，补齐近 30 年窗口中的居民活期存款数据。
- 推送中心日报市场摘要表格在手机端将字号压缩到 12px，缓解指数数据列在窄屏邮箱中的拥挤问题。
- Market Data 的全国 70 城二手房价格指数从单一同比 100 基准指数扩展为同比、环比和全局走势三组序列；同比/环比统一展示为相对 100 的百分比变化，全局走势使用环比从历史首期前值 100 连续复合。
- 顶部 Header、模块工作区和侧栏一级模块不再展示描述性副标题；侧栏折叠态为 Market Data、Trend Models、Push Center 分别使用不同 Heroicons 图标。
- 推送中心日报内联 SVG 图表改为百分比宽度与 `max-width:100%`，降低手机端 QQ 邮箱裁切图表的概率。
- Dashboard / News / Macro / Market / Events / Status 前端页面已清空并从导航与默认入口移除；`/api/dashboard`、`/api/frontend/dashboard`、`/api/frontend/modules/status`、`/legacy` 与对应页面 SPA 入口移除，Push Center 后端接口保留。
- News / Market / Events 顶层模块移除页内子 tab 与侧栏子目录，页面统一展示单页总览；`/api/frontend/modules/news|market|events` 独立后端接口移除，前端改从 `/api/frontend/dashboard` 聚合 payload 读取对应模块数据。
- Macro 顶层模块移除页内子 tab、侧栏子目录和 `/api/frontend/modules/macro` 独立后端接口；`/macro` 改为从 `/api/frontend/dashboard` 的 `macro_sections` 渲染单页总览。
- 修复推送中心“页面预览与实际发送日报图表不一致”的分叉：页面加载预览时默认请求最新快照，手动发送会在配置匹配时直接复用当前预览 HTML，保证所见即所得。
- 修复推送中心模块级日报预览标题与摘要的中文乱码问题，模块级 preview 的标题文案恢复为可读中文。
- 推送中心日报预览 iframe 改为按内容高度自动拉伸，减少预览区内部竖向滚动条的出现频率。
- 统一推送中心与旧 `push_job` 的邮件报告生成链路：邮件发送现在也复用 HTML 日报渲染结果，避免出现“预览图表已更新但实际收到的邮件仍沿用旧 markdown 内容”的分叉。
- 推送中心改为按页面上下文裁剪预览开销：`History` 标签页请求可跳过 preview 构建，推送预览也优先按已选模块组装，避免普通加载被全量 dashboard snapshot 拖慢。
- 推送中心 `Schedules` 页面加载时不再默认携带 `refresh=1` 强制刷新预览，避免每次刷新页面都绕过本地缓存触发重型数据同步；手动 `Refresh preview` 仍会请求最新预览。
- 推送中心移除冗余 `Overview` 页面与侧栏子目录；旧 `tab=overview` 链接会自动归一到 `tab=schedules`，保留配置、计划与历史操作入口。
- 推送中心配置表单移除冗余 `Config path` 展示块，减少页面头部无操作价值的信息。
- 推送中心布局调整为「左侧配置/计划约三分之一，右侧预览约三分之二」；同时移除预览里的 `Text fallback`，并删除 `Schedules` 标签页的冗余发送历史侧栏与 `History` 标签页的预览侧栏。
- 推送中心 `History` 页面移除冗余 `Run controls` 卡片，仅保留推送运行历史记录。
- Settings 页面移除冗余正文卡片和默认入口偏好表单，仅保留应用壳层中的 Settings 路由入口。
- 修复推送中心日报中市场模块“表格值已刷新但趋势图尾点仍停留旧值”的展示错位问题；日报图表渲染现在会优先与表格侧最新 `trade_date / close / MA20 / deviation` 对齐。
- 前端浏览器标签页标题由 `AI News Bot` 调整为 `Trend Insight`，与当前产品命名保持一致。
- 宏观数据页升级为配对研究视图：按相关指标成对展示 `relative performance / spread / raw series` 图表，复用现有 `points / delta_points` 数据生成更贴近量化研究工作流的 ECharts 可视化。
- 文档体系从“任务导向”补齐为“工程基线导向”，新增架构/API/测试三个长期维护文档。
- 前端侧栏导航从 `Workspace` 分组卡片调整为「Dashboard 独立 + News/Macro/Market/Events/Push Center 一级目录」，并为各模块提供子目录入口。
- 移除侧栏冗余文案 `Research Desk` 与 `Loading workspace...`。
- `News mode` 开关从全局 Header 下沉到 `News` 模块页内，和新闻子标签统一管理。
- 事件模块标签改为 `近一周 / 近1个月 / 近6个月` 三档时间窗口，并按时间范围过滤事件卡片展示。
- 主题切换组件升级为显式 `Light / Dark` 双按钮样式，并补充暗色主题全局样式覆盖。
- 侧栏选中态视觉权重下调：主模块与子模块的激活样式由深底改为浅底，减少视觉压迫。
- 子模块激活时不再同时高亮对应主模块，避免双重选中提示。
- 侧栏折叠按钮位置调整到右上区域，并替换为双栏风格图标。
- 侧栏折叠态移除冗余 `TI` 品牌占位，并将 `Push Center`、`Settings` 导航从文字缩写替换为 Heroicons 图标；项目 UI 约定同步要求后续图标优先使用 Heroicons。
- 推送中心顶部 `Updated` 与历史执行时间改为浏览器本地时区展示，并新增前端本地时间格式化约定，避免界面继续硬编码 UTC。
- 侧栏导航改为“模块区可滚动 + System 区固定底部”，模块过多时不再挤压底部系统入口。
- 应用壳层改为固定视口高度，主内容区启用内部纵向滚动，News 等长页面可在页面内滚动浏览。
- 顶部模块概览改为同排布局：模块标题/Freshness 小字、主题切换与大盘数据概览位于同一行。
- 大盘数据概览补齐核心指数位（含恒生指数、创业板指），并在超宽内容下启用横向滚动。
- 侧栏标题与折叠按钮对齐到同一行，减少顶部占位高度。
- 顶部 Header 移除 `Freshness` 时间文案展示，仅保留模块标题与核心控制。
- 大盘数据概览卡片移除日期字段，保留指数名、来源、数值与信号信息。
- 暗色主题覆盖规则修复，补齐 `bg-slate-200` 与图标描边/填充映射，并移除异常偏色覆盖。
- 顶部 Header 调整为三列稳定布局：左标题、中部横向滚动指数条、右侧主题按钮固定最右。
- 指数条支持滚轮驱动的横向滚动，且卡片间距与内部排版收紧。
- 主题切换按钮图标与配色样式重绘，修复显示异常与编码问题。
- 顶部主题切换区移除 `Theme` 标签文案，仅保留明暗模式切换按钮。
- 左侧模块目录改为“首次进入按默认折叠，后续刷新保持刷新前的展开/折叠状态”。
- 路由壳测试补强为覆盖 Header 紧凑布局、ticker 横向滚动存在性，以及模块目录默认折叠的回归场景。
- 下线 NewsNow provider 运行链路：DashboardService 实时新闻改为公共 RSS + 样例兜底，后台缓存刷新不再预热 `hybrid/api/upstream` 新闻模式，也不会再访问本地 `127.0.0.1:5173` NewsNow 服务。

## [2026-04-01]

### Added

- 前端左侧导航支持整栏折叠/展开。
- 左侧导航支持分组卡片（大标题）折叠/展开子项。
- 前端路由壳测试新增侧栏折叠与分组折叠回归用例。

### Changed

- `frontend/src/layouts/app-shell.tsx` 改为可折叠侧栏布局。
- `frontend/src/layouts/sidebar-nav.tsx` 从扁平导航升级为分组导航。
- `frontend/src/shared/config/nav-items.ts` 新增导航分组模型。

## [2026-03-30]

### Added

- 前端迁移差距审计文档：`docs/frontend-migration-gap-audit-2026-03-30.md`。
- Frontend Shell 相关设计与计划文档（`docs/superpowers/specs/` 与 `docs/superpowers/plans/`）。

### Changed

- 明确新前端 SPA 与 legacy 前端并存阶段的边界与迁移顺序。

## [2026-03-xx] - Task 里程碑阶段（汇总）

### Added

- 完成任务链路文档 `tasks/01` 到 `tasks/10`（架构、数据源、壳层、新闻、宏观、市场、事件、推送、测试、本地环境）。
- 补充配套测试矩阵（`tests/test_task01_*.py` 到 `tests/test_task11_*.py`）。

### Notes

- 该阶段以“从脚本到平台化”重构为主线，细粒度提交记录请结合 Git 历史查看。

## [2026-04-29] - 测试冗余清理

### Changed

- 移除 `tests/test_task02` 到 `tests/test_task09` 中仅校验任务文档存在性的冗余测试。
- 将阶段性 demo / smoke 测试与重复度较高的历史测试归档到 `to_delete/tests/`。
- 同步更新 `docs/test-strategy.md` 与 `.vscode/launch.json`，避免引用已归档测试。

---

维护约定：

- 每个可感知行为变化（功能/接口/测试门禁）都应追加 changelog。
- 若为 breaking change，需在条目中明确“影响范围 + 迁移建议”。
