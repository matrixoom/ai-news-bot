# 股票估值与财务质量指标实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为股票详情页增加四项日频估值指标和四项季度财务指标，并完成分片存储、接口返回与图表展示。

**Architecture:** 日频估值字段扩展现有 `market_stock_daily_bar` 分片表，仓储负责兼容迁移和读写；同步服务将东方财富估值历史及分红事件按交易日合并。季度指标继续写入 `market_stock_financial_metric`，详情 Service 保持现有响应层级，只追加字段和序列。

**Tech Stack:** Python 3.12、SQLite、FastAPI、AkShare、pytest、React 18、TypeScript、ECharts、Vitest

---

### Task 1: 日线分片 schema 与仓储读写

**Files:**
- Modify: `src/services/stock_market_sharding.py`
- Modify: `src/services/stock_market_repository.py`
- Test: `tests/test_market_data_module.py`

- [ ] **Step 1: 编写失败测试**

新增测试验证：

```python
def test_stock_shard_initializer_adds_valuation_columns_to_existing_table():
    # 先创建不含新列的旧表，再初始化并断言四列均存在。
    ...

def test_daily_bar_upsert_round_trips_valuation_metrics():
    # 写入并重复更新 pe_ttm、pb_mrq、dividend_yield_ttm、total_market_cap。
    ...
```

同时扩展旧主库迁移测试，旧表包含新列时迁移后值不丢失，旧表不含新列时仍可迁移。

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
uv run --python 3.12 python -m pytest tests/test_market_data_module.py -k "valuation_columns or valuation_metrics or legacy_stock" -v
```

Expected: FAIL，原因是 schema 和 `StockDailyBar` 尚无估值字段。

- [ ] **Step 3: 实现最小 schema 与仓储改动**

在分片初始化时读取 `PRAGMA table_info(market_stock_daily_bar)`，对缺失列逐一执行：

```sql
ALTER TABLE market_stock_daily_bar ADD COLUMN pe_ttm REAL;
ALTER TABLE market_stock_daily_bar ADD COLUMN pb_mrq REAL;
ALTER TABLE market_stock_daily_bar ADD COLUMN dividend_yield_ttm REAL;
ALTER TABLE market_stock_daily_bar ADD COLUMN total_market_cap REAL;
```

扩展 `StockDailyBar`、日线 upsert、load、旧表迁移和行构造。旧表迁移先检测源列，缺失字段使用
`NULL AS column_name`，保证从任意历史版本升级。

- [ ] **Step 4: 运行测试确认通过**

Run:

```powershell
uv run --python 3.12 python -m pytest tests/test_market_data_module.py -k "stock_shard or daily_bar or legacy_stock" -v
```

Expected: PASS。

### Task 2: 估值与季度财务数据同步

**Files:**
- Modify: `src/services/stock_market_sync_service.py`
- Test: `tests/test_market_data_module.py`

- [ ] **Step 1: 编写失败测试**

新增以下行为测试：

```python
def test_valuation_rows_merge_by_trade_date_and_compute_ttm_dividend_yield():
    # PE/PB/市值按日期合并；过去 365 天两次每 10 股派息合计后除以收盘价。
    ...

def test_valuation_source_failure_keeps_daily_bars_available():
    # 估值或分红 loader 抛错时，OHLCV 仍写入且估值字段为 None。
    ...

def test_financial_analysis_extracts_quarterly_quality_metrics():
    # 从 REPORT_DATE、ROEJQ、TOTALOPERATEREVETZ、PARENTNETPROFITTZ、ZCFZL 解析四项百分比。
    ...
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
uv run --python 3.12 python -m pytest tests/test_market_data_module.py -k "valuation_rows or valuation_source or financial_analysis" -v
```

Expected: FAIL，原因是新 loader 和解析函数不存在。

- [ ] **Step 3: 实现日频估值同步**

为 `StockMarketSyncService` 增加可注入的 `valuation_loader` 和 `dividend_loader`，默认分别调用：

```python
ak.stock_value_em(symbol=code)
ak.stock_fhps_detail_em(symbol=code)
```

实现纯函数：

```python
def _valuation_rows_from_frames(
    bars: Sequence[Mapping[str, Any]],
    valuation_frame: Any,
    dividend_frame: Any,
) -> list[dict[str, Any]]:
    ...
```

按 `数据日期` 读取 `PE(TTM)`、`市净率`、`总市值`；只纳入 `方案进度` 包含“实施”的分红，
以 `除权除息日` 和 `现金分红-现金分红比例 / 10` 计算滚动 365 日股息率。

- [ ] **Step 4: 实现季度财务指标解析**

新增 `financial_analysis_loader`，默认调用：

```python
ak.stock_financial_analysis_indicator_em(symbol=instrument.symbol, indicator="按报告期")
```

解析时兼容东方财富字段名和中文测试字段名：

```python
specs = [
    ("roe", "ROE", "%", ["ROEJQ", "净资产收益率"]),
    ("revenue_yoy", "营收同比", "%", ["TOTALOPERATEREVETZ", "营业总收入同比增长"]),
    ("net_profit_yoy", "净利润同比", "%", ["PARENTNETPROFITTZ", "归属净利润同比增长"]),
    ("debt_asset_ratio", "资产负债率", "%", ["ZCFZL", "资产负债率"]),
]
```

将结果与现有五项财务指标合并后统一 upsert。

- [ ] **Step 5: 运行测试确认通过**

Run:

```powershell
uv run --python 3.12 python -m pytest tests/test_market_data_module.py -k "valuation or financial" -v
```

Expected: PASS。

### Task 3: 详情 API 契约

**Files:**
- Modify: `src/services/stock_market_service.py`
- Modify: `docs/api-contract.md`
- Modify: `CHANGELOG.md`
- Test: `tests/test_market_data_module.py`

- [ ] **Step 1: 编写失败测试**

扩展详情 payload 测试，断言：

```python
payload["daily_bars"][0]["pe_ttm"] == 5.1
payload["daily_bars"][0]["pb_mrq"] == 0.48
payload["daily_bars"][0]["dividend_yield_ttm"] == 3.2
payload["daily_bars"][0]["total_market_cap"] == 2130.77
```

并断言 `financials.series` 顺序为原五项加
`roe`、`revenue_yoy`、`net_profit_yoy`、`debt_asset_ratio`。

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
uv run --python 3.12 python -m pytest tests/test_market_data_module.py -k "stock_detail" -v
```

Expected: FAIL，详情 payload 尚未暴露新字段。

- [ ] **Step 3: 实现兼容式响应扩展**

在 `_build_detail_payload()` 将库存元换算为亿元：

```python
"total_market_cap": (
    round(bar.total_market_cap / 100_000_000, 4)
    if bar.total_market_cap is not None
    else None
)
```

扩展 `_financial_payload()` 的顺序和标签映射，保持现有结构不变。

- [ ] **Step 4: 更新接口文档和变更日志**

在 `docs/api-contract.md` 记录字段、单位、可空性和财务 metric；在 `CHANGELOG.md` 记录兼容策略：
只新增字段，不删除或改名。

- [ ] **Step 5: 运行测试确认通过**

Run:

```powershell
uv run --python 3.12 python -m pytest tests/test_market_data_module.py -k "stock_detail or financial" -v
```

Expected: PASS。

### Task 4: K 线与财务页图表

**Files:**
- Modify: `frontend/src/features/market-data/model/market-data.types.ts`
- Modify: `frontend/src/features/market-data/components/stock-market-workspace.tsx`
- Modify: `frontend/src/features/market-data/__tests__/stock-market-workspace.test.tsx`

- [ ] **Step 1: 编写失败测试**

扩展 mock 日线和财务序列，新增断言：

```typescript
expect(klineOption.legend?.right).toBe(8);
expect(klineOption.legend?.data).toEqual(
  expect.arrayContaining(["PE(TTM)", "PB(MRQ)", "股息率(TTM)", "总市值"]),
);
expect(seriesByName["PE(TTM)"].data).toEqual([5.1, null]);
expect(screen.getByRole("tab", { name: "ROE" })).toBeInTheDocument();
expect(financialOption.series?.[0].type).toBe("line");
```

同步调整用户已有的复权按钮测试，使其匹配当前只展示“不复权”的界面状态。

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
npm --prefix frontend test -- --run src/features/market-data/__tests__/stock-market-workspace.test.tsx
```

Expected: FAIL，类型和图表配置尚无新指标。

- [ ] **Step 3: 扩展类型与 K 线图表**

为 `StockDailyBar` 增加四个 `number | null` 字段。K 线图例使用：

```typescript
legend: {
  top: 8,
  right: 8,
  orient: "vertical",
  type: "scroll",
}
```

为四项指标添加独立隐藏 yAxis 和折线 series，设置 `connectNulls: false`。右侧为图例预留宽度，
成交量继续使用原独立网格。

- [ ] **Step 4: 扩展财务页签与图表类型**

更新 `FINANCIAL_ORDER`。`FinancialMetricCard` 对 `%` 单位指标统一使用折线图，亿元金额指标
保持现有柱线策略。

- [ ] **Step 5: 运行目标测试和前端构建**

Run:

```powershell
npm --prefix frontend test -- --run src/features/market-data/__tests__/stock-market-workspace.test.tsx
npm --prefix frontend run build
```

Expected: PASS，构建 exit code 0。

### Task 5: 实体分片迁移、完整回归与提交

**Files:**
- Modify: `.data/market/SH/*.db`
- Modify: `.data/market/SZ/*.db`
- Modify: `.data/market/BJ/*.db`
- Modify: `.data/market_data.db`
- Modify: `docs/股票数据分库分表设计.md`

- [ ] **Step 1: 更新分片文档**

记录四个新增可空列、库存单位、初始化迁移命令和缺失值策略。

- [ ] **Step 2: 迁移实体数据库**

Run:

```powershell
uv run --python 3.12 python -c "from src.services.stock_market_repository import StockMarketRepository; StockMarketRepository()"
```

验证全部 210 个分片都有四列：

```powershell
uv run --python 3.12 python -c "from pathlib import Path; import sqlite3; paths=list(Path('.data/market').glob('*/*.db')); assert len(paths)==210; assert all({'pe_ttm','pb_mrq','dividend_yield_ttm','total_market_cap'} <= {r[1] for r in sqlite3.connect(p).execute('PRAGMA table_info(market_stock_daily_bar)')} for p in paths)"
```

- [ ] **Step 3: 运行完整验证**

Run:

```powershell
uv run --python 3.12 python -m pytest
uv run --python 3.12 python -m compileall -q src tests
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Expected: 全部命令 exit code 0。

- [ ] **Step 4: 检查变更并提交**

Run:

```powershell
git diff --check
git status --short
git add -A
git commit -m "feat: add stock valuation and financial indicators"
```

提交需包含代码、测试、文档、用户已有修改以及 `.data/*.db` 和 210 个分片数据库变更。
