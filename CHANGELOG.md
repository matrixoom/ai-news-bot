# 变更记录（Changelog）

本项目遵循“按时间倒序记录”的方式维护变更日志。建议参考 Keep a Changelog 思路，结合本仓库实际调整。

## [Unreleased]

### Added

- 新增 `AGENTS.md`，统一 Codex/代理协作与变更规则。
- 新增 `docs/architecture.md`，明确架构分层与模块边界。
- 新增 `docs/api-contract.md`，固化前后端接口契约与错误语义。
- 新增 `docs/test-strategy.md`，固化测试分层与回归门禁。

### Changed

- 文档体系从“任务导向”补齐为“工程基线导向”，新增架构/API/测试三个长期维护文档。

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
