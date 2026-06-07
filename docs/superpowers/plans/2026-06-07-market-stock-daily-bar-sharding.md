# 股票日线分库实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按交易所与股票代码特定位拆分 `market_stock_daily_bar`，预建 210 个 SQLite 分库，并无损迁移主库已有日线数据。

**Architecture:** `market_data.db` 继续保存标的、概况、财报和同步状态；独立的分片路由模块负责校验 symbol、解析分片路径、初始化分片 schema。股票仓储按 symbol 路由日线读写，列表页按分片批量读取最新价，初始化时幂等迁移旧表并在完整性校验通过后移除旧表。

**Tech Stack:** Python 3.12、SQLite、pytest

---

### Task 1: 分片路由与预建

**Files:**
- Create: `src/services/stock_market_sharding.py`
- Test: `tests/test_market_data_module.py`

- [ ] **Step 1: 编写失败测试**

覆盖 SH/SZ 第 4、5 位、BJ 最后一位、非法 symbol 拒绝，以及预建后存在 210 个数据库且每库包含 `market_stock_daily_bar` 表和唯一索引。

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_market_data_module.py -k "stock_shard" -v`

Expected: FAIL，原因是分片模块和接口尚不存在。

- [ ] **Step 3: 实现最小路由和 schema 初始化**

实现 `resolve_market_stock_shard_name()`、`resolve_market_stock_shard_path()`、`iter_market_stock_shard_paths()`、`initialize_market_stock_shard()` 和 `initialize_all_market_stock_shards()`；仅允许 `SH`、`SZ`、`BJ`，分片表以 `(symbol, trade_date)` 为主键，不声明跨库外键。

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_market_data_module.py -k "stock_shard" -v`

Expected: PASS。

### Task 2: 旧表迁移与日线读写路由

**Files:**
- Modify: `src/services/stock_market_repository.py`
- Test: `tests/test_market_data_module.py`

- [ ] **Step 1: 编写失败测试**

覆盖旧主库日线按 symbol 迁入正确分片、迁移后旧表消失、重复初始化幂等、日线 upsert/读取/存在性判断均访问分片，以及同步状态聚合仍正确。

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_market_data_module.py -k "daily_bar or legacy_stock" -v`

Expected: FAIL，原因是仓储仍访问主库日线表。

- [ ] **Step 3: 实现迁移和路由访问**

仓储初始化主库元数据表后执行旧表迁移；迁移逐分片复制并校验，遇到非法 symbol 或缺失记录时保留旧表并抛出明确异常。`upsert_daily_bars()`、`has_daily_bars()`、`load_daily_bars()` 和同步状态聚合改用目标分片连接。

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_market_data_module.py -k "daily_bar or legacy_stock" -v`

Expected: PASS。

### Task 3: 股票列表最新价兼容

**Files:**
- Modify: `src/services/stock_market_repository.py`
- Test: `tests/test_market_data_module.py`

- [ ] **Step 1: 编写失败测试**

建立跨 SH、SZ、BJ 分片的标的和日线，断言分页搜索返回各自最新收盘价，且无行情标的返回 `None`。

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_market_data_module.py -k "latest_price" -v`

Expected: FAIL，原因是列表 SQL 仍关联主库旧表。

- [ ] **Step 3: 实现按分片批量补价**

主库仅查询标的分页；按分片对当前页 symbol 分组，每个分片执行一次批量最新价查询，再构造 `StockInstrument`，避免逐标的 N+1。

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_market_data_module.py -k "latest_price" -v`

Expected: PASS。

### Task 4: 文档、实体分库与回归

**Files:**
- Modify: `docs/股票数据分库分表设计.md`
- Modify: `docs/architecture.md`
- Modify: `CHANGELOG.md`
- Create: `.data/market_stock_SH_00.db` 至 `.data/market_stock_SH_99.db`
- Create: `.data/market_stock_SZ_00.db` 至 `.data/market_stock_SZ_99.db`
- Create: `.data/market_stock_BJ_0.db` 至 `.data/market_stock_BJ_9.db`
- Modify: `.data/market_data.db`

- [ ] **Step 1: 补充迁移、兼容与运维说明**

记录主库与分片库职责、迁移顺序、失败保留策略、预建命令、回归命令，以及 SQLite 跨库外键限制。

- [ ] **Step 2: 运行预建和迁移**

使用仓储初始化逻辑预建 210 个分片并迁移 `.data/market_data.db` 的既有日线；检查旧表不存在、分片总行数与迁移前一致。

- [ ] **Step 3: 运行完整验证**

Run: `pytest`

Expected: 全部测试 PASS。

Run: `python -m compileall src tests`

Expected: exit code 0。

- [ ] **Step 4: 暂存并提交**

Run: `git add -A`

Run: `git commit -m "feat: shard stock daily market data"`

Expected: 提交包含代码、测试、文档和预建 SQLite 分库。
