# Task 01 Migration Backlog

## Phase 0: Freeze Old Flow

- 保持 `main.py` 当前行为可运行
- 不在旧入口上继续加新业务
- 后续新增功能全部优先进入新结构

## Phase 1: Build New Skeleton

- 建立 `src/app`
- 建立 `src/domain`
- 建立 `src/services`
- 建立 `src/providers`
- 建立 `src/delivery`

## Phase 2: Create Compatibility Adapters

- 旧 `src/news` 暂时继续服务推送逻辑
- 旧 `src/notifiers` 暂时作为 delivery 兼容实现
- 旧 `src/llm_providers` 暂时作为 provider 兼容实现

## Phase 3: Move Or Wrap

- 把旧 `Config` 包装为 settings provider
- 把旧 `NewsGenerator` 的编排职责迁到 service
- 把旧通知逻辑迁到 delivery gateway

## Phase 4: Switch Entrypoints

- 新建 Web 入口
- 将 `main.py` 改造成 push job 入口
- GitHub Actions 继续调用 push job

## Exit Criteria

- Web 与 push 入口都不再直接访问旧的抓取编排逻辑
- 服务层可以独立产出 dashboard data 和 push report data
