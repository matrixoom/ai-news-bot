# AGENTS 规则（Codex 协作总则）

## 1. 项目概述（优先）

本项目为“趋势洞察”系统，聚焦：财经分析、科技趋势、数据洞察、信息聚合与解读。

核心目标：

- 快速迭代 + 高稳定性
- 架构清晰、易维护
- 支持数据源/分析模型/可视化扩展
- 数据驱动与模块化设计

决策与价值优先级：

- 用户当前明确需求 > 系统稳定与可回归 > 兼容性 > 代码整洁度 > 开发便利性
- 稳定性 > 技巧炫技
- 可维护性 > 短期开发速度
- 清晰结构 > 复杂抽象

## 2. 代码边界与技术栈约束
注释：
- 所有代码必须添加清晰、必要的注释，不写无意义注释，不写冗余注释。
- 函数 / 类必须标注用途、参数含义、返回值；复杂逻辑必须说明思路。
- 注释使用中文，保持统一、易读、格式规范。

目录边界：

- 后端主代码：`src/`
- 前端 SPA：`frontend/`
- 测试：`tests/` 与 `frontend/src/**/__tests__/`
- 文档：`docs/`、`tasks/`
- 第三方子模块：`.third_part_newsnow/`（默认不可修改）

技术栈（默认不偏离）：

- 前端：`TypeScript + Vite`、`React 18`、`react-router-dom`、`@tanstack/react-query`、`Tailwind CSS`、`Vitest + Testing Library`、`ECharts`
- 后端：`Python 3.12`、`FastAPI + uvicorn`、`httpx`（默认）/`requests`（兼容）、`pytest`

约束：

- 未经明确要求，不修改第三方子模块源码。
- 未经明确要求，不删除历史文件，所有认为哟删除的统一先归档到to_delete目录。


## 3. 设计与架构原则（必须遵守）

通用原则：

- 高内聚低耦合：单一职责、接口通信、禁止隐式跨模块依赖、禁止循环依赖。
- 易扩展：包括但不限于：策略模式/配置驱动/插件式设计等，避免 if-else 扩散。
- 易测试：核心逻辑可单测，IO 与业务逻辑分离，避免静态全局状态，逻辑可重复执行（deterministic）。
- 简单优先：避免过度设计，遵循 YAGNI。

架构分层：

- 后端严格三层：`Controller`（参数校验+返回）/ `Service`（业务逻辑）/ `Repository`（数据访问）。
- 禁止 Controller 写业务、禁止 Service 直接操作 DB、禁止跨层混乱调用。
- 前端采用组件化，分离 UI（展示）/ state（状态）/ API（请求）。
- 单组件超过 300 行应评估拆分，避免逻辑与 UI 混杂。

数据层：

- schema 清晰、禁止隐式字段、字段变更可追踪、保持向后兼容。

## 4. 接口、稳定性与后端重点约束

接口与兼容：

- 前端接口优先使用 `/api/frontend/*`。
- 禁止随意修改接口契约；返回结构保持稳定；错误码统一管理。
- 改动响应字段时，必须同步更新 adapter/types、相关测试，并在 `docs/api-contract.md` 与 `CHANGELOG.md` 记录兼容策略。


后端工程约束：

- 禁止吞异常；必须记录可定位日志；对外返回友好错误信息。
- 日志需包含关键上下文（如 `traceId`、关键参数），禁止输出敏感信息。
- 避免 N+1，优先批量操作，关注并发安全。
- 输入校验严格，快速失败（fail-fast），不得影响现有功能。

前端与 UI 约束：

- UI 风格简洁、专业、数据优先，信息层级清晰。
- 前端所有新增或替换图标统一使用 Heroicons（优先 `@heroicons/react/24/outline`），禁止用字符缩写或临时自绘 SVG 充当常规 UI 图标；确需自定义图标时必须先说明原因并获得明确确认。
- 前端所有展示给用户看的时间必须使用浏览器本地时区格式化；优先复用 `frontend/src/shared/utils/format-local-date-time.ts`，禁止在界面层硬编码 `UTC` 作为展示时区，除非用户明确要求。
- 图表必须具备标题、单位、图例。
- 禁止重复实现同类组件，优先复用与抽象通用组件。
- 保持响应式与基础可访问性（语义化、焦点可见、对比度、表单可用性）。

## 5. 变更流程（强制）

开发前：

1. 理解需求与现有代码（至少入口/实现/测试三处）
2. 识别影响范围与风险


开发中：

1. 维持分层与兼容，不引入隐藏副作用
2. 修复问题时必须同步检查上下游关联链路

开发后：

1. 列出修改文件与变更摘要
2. 给出验证命令与结果
3. 说明风险与后续建议

## 6. 测试、回归与构建门禁（强制）

每次修改至少满足其一：

- 补充单元测试；或
- 提供明确人工验证步骤

测试重点：核心业务逻辑、边界条件、异常路径。

回归检查清单（输出必带）：

1. 原功能验证点
2. 新功能验证点
3. 边界情况
4. 异常处理
5. 配置兼容性

任务完成前必须满足：测试通过、构建成功、无明显代码错误、无依赖问题。

## 7. Git、安全与禁止行为

- 禁止破坏性命令：`git reset --hard`、`git checkout -- <file>` 、`git push --force` 等高危命令（除非用户明确授权）。
- 禁止直接删除本地文件；删除需求统一先移动到 `to_delete/`。


## 8. 文档与提交规范

文档：

- 新功能或行为变化，至少同步更新一处：`README.md`、`docs/architecture.md`、`docs/api-contract.md`、`docs/test-strategy.md`、`CHANGELOG.md`。
- 文档必须包含可执行信息：命令、路径、接口、状态码、回归方式。

提交：

- 推荐 Conventional Commits：`feat:`、`fix:`、`refactor:`、`docs:`、`test:`。

## 9. Codex 输出格式（默认）

非简单任务默认按以下结构输出：

1. 需求理解
2. 影响分析
3. 实现方案
4. 修改内容
5. 验证方式
6. 风险与建议

## 10. 验证后提交
After every complete file edit, check if the test suite passes. If all tests pass, stage all changed files, generate a conventional commit message summarizing the changes: what was changed, why, and which files were affected. If tests fail, analyze the failure output, fix the code, and re-run tests up to 3 times before asking for help.