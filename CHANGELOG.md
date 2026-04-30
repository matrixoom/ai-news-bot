# 变更记录（Changelog）

本项目遵循“按时间倒序记录”的方式维护变更日志。建议参考 Keep a Changelog 思路，结合本仓库实际调整。

## [Unreleased]

### Added

- 新增 `AGENTS.md`，统一 Codex/代理协作与变更规则。
- 新增 `docs/architecture.md`，明确架构分层与模块边界。
- 新增 `docs/api-contract.md`，固化前后端接口契约与错误语义。
- 新增 `docs/test-strategy.md`，固化测试分层与回归门禁。

### Changed

- Dashboard / News / Macro / Market / Events 前端页面已清空并从导航与默认入口移除；`/api/dashboard`、`/api/frontend/dashboard`、`/legacy` 与对应页面 SPA 入口移除，Push Center 与 Status 后端接口保留。
- News / Market / Events 顶层模块移除页内子 tab 与侧栏子目录，页面统一展示单页总览；`/api/frontend/modules/news|market|events` 独立后端接口移除，前端改从 `/api/frontend/dashboard` 聚合 payload 读取对应模块数据。
- Macro 顶层模块移除页内子 tab、侧栏子目录和 `/api/frontend/modules/macro` 独立后端接口；`/macro` 改为从 `/api/frontend/dashboard` 的 `macro_sections` 渲染单页总览。
- 修复推送中心“页面预览与实际发送日报图表不一致”的分叉：页面加载预览时默认请求最新快照，手动发送会在配置匹配时直接复用当前预览 HTML，保证所见即所得。
- 修复推送中心模块级日报预览标题与摘要的中文乱码问题，模块级 preview 的标题文案恢复为可读中文。
- 推送中心日报预览 iframe 改为按内容高度自动拉伸，减少预览区内部竖向滚动条的出现频率。
- 统一推送中心与旧 `push_job` 的邮件报告生成链路：邮件发送现在也复用 HTML 日报渲染结果，避免出现“预览图表已更新但实际收到的邮件仍沿用旧 markdown 内容”的分叉。
- 推送中心改为按页面上下文裁剪预览开销：`History` 标签页请求可跳过 preview 构建，推送预览也优先按已选模块组装，避免普通加载被全量 dashboard snapshot 拖慢。
- 推送中心布局调整为「左侧配置/计划约三分之一，右侧预览约三分之二」；同时移除预览里的 `Text fallback`，并删除 `Schedules` 标签页的冗余发送历史侧栏与 `History` 标签页的预览侧栏。
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

---

维护约定：

- 每个可感知行为变化（功能/接口/测试门禁）都应追加 changelog。
- 若为 breaking change，需在条目中明确“影响范围 + 迁移建议”。
