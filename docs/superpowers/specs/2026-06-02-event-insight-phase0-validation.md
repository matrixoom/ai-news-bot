# Event Insight P0 技术验证记录

## 1. 验证范围

本记录用于关闭 Event Insight 后续 P2/P5/P7/P9 会依赖的环境敏感决策。P0 不新增生产代码、不新增接口、不修改现有 Outlook 静态日历行为。

验证日期：2026-06-03  
验证分支：`feature/event-insight-p0-validation`  
验证环境：Windows, Python 3.12.12, SQLite 3.50.4, Node.js 24.13.1

## 2. 结论摘要

```text
1. sqlite-vec 可以在当前 Python 3.12 环境通过 uv 临时依赖加载。
2. SQLite FTS5 已启用，但 unicode61 对中文短词召回不足。
3. 中文检索 P7 需要在 FTS5 外增加应用层 2-gram/3-gram 辅助列。
4. 当前环境没有 Docker 命令，Neo4j 不能在本机验证启动；P9 必须把 Neo4j 作为可选投影依赖。
5. 前端图谱第一版优先复用已存在的 ECharts 6 graph series，暂不引入 G6/Cytoscape/React Flow。
6. P5 应统一现有 BaseLLMProvider、OpenAI/DeepSeek Provider 和 ArkResearchProvider，避免事件洞察产生第三套 LLM 调用链。
```

## 3. sqlite-vec 验证

安装/临时运行命令：

```powershell
uv run --with sqlite-vec python -c "import sqlite3, sqlite_vec; print('python', __import__('sys').version.split()[0]); print('sqlite', sqlite3.sqlite_version); print('sqlite_vec', sqlite_vec.__version__)"
```

输出摘要：

```text
python 3.12.12
sqlite 3.50.4
sqlite_vec 0.1.9
```

扩展加载和虚拟表 DDL：

```python
import sqlite3
import sqlite_vec

conn = sqlite3.connect(":memory:")
conn.enable_load_extension(True)
sqlite_vec.load(conn)
conn.enable_load_extension(False)
conn.execute(
    "CREATE VIRTUAL TABLE event_embedding "
    "USING vec0(event_id integer primary key, embedding float[4])"
)
```

查询验证：

```python
conn.execute(
    "INSERT INTO event_embedding(event_id, embedding) VALUES (?, ?)",
    (1, "[0.10, 0.20, 0.30, 0.40]"),
)
conn.execute(
    "INSERT INTO event_embedding(event_id, embedding) VALUES (?, ?)",
    (2, "[0.90, 0.10, 0.10, 0.10]"),
)
rows = conn.execute(
    "SELECT event_id, distance FROM event_embedding "
    "WHERE embedding MATCH ? AND k = 2",
    ("[0.10, 0.20, 0.31, 0.39]",),
).fetchall()
```

输出摘要：

```text
[(1, 0.014142143540084362), (2, 0.8821563720703125)]
```

后续约束：

```text
P7 再把 sqlite-vec 写入 requirements.txt 和 migration。
P2 不创建 vec0 表，避免在地基阶段引入可选扩展依赖。
Repository 初始化 sqlite-vec 时必须有明确错误信息和 FTS-only 降级路径。
```

## 4. FTS5 中文召回验证

原生 FTS5 验证命令：

```powershell
@'
import sqlite3
conn = sqlite3.connect(':memory:')
opts = [row[0] for row in conn.execute('pragma compile_options')]
print('sqlite', sqlite3.sqlite_version)
print('fts5', any('ENABLE_FTS5' in opt for opt in opts))
conn.execute("CREATE VIRTUAL TABLE docs USING fts5(title, body, tokenize='unicode61')")
rows = [
    ('HBM4 量产节奏提前', '三星与 SK 海力士推进 HBM4，先进封装产能继续吃紧。'),
    ('存储芯片报价上调', 'DRAM 合约价上涨，AI 服务器需求支撑内存涨价。'),
]
conn.executemany('INSERT INTO docs(title, body) VALUES (?, ?)', rows)
for q in ['HBM4', '内存', '存储芯片', '涨价', '先进封装', 'AI服务器']:
    result = list(conn.execute('SELECT title FROM docs WHERE docs MATCH ? ORDER BY rank', (q,)))
    print(q, len(result), [r[0] for r in result])
'@ | uv run python -
```

输出摘要：

```text
sqlite 3.50.4
fts5 True
HBM4 1 ['HBM4 量产节奏提前']
内存 0 []
存储芯片 0 []
涨价 0 []
先进封装 0 []
AI服务器 0 []
```

结论：

```text
unicode61 可用于英文、数字和部分混合 token，但不能作为中文财经短语的唯一召回方案。
```

应用层 n-gram 辅助列验证：

```powershell
@'
import sqlite3

def grams(text, min_n=2, max_n=3):
    compact = ''.join(ch.lower() for ch in text if not ch.isspace())
    result = []
    for n in range(min_n, max_n + 1):
        result.extend(compact[i:i+n] for i in range(max(0, len(compact) - n + 1)))
    return ' '.join(result)

conn = sqlite3.connect(':memory:')
conn.execute("CREATE VIRTUAL TABLE docs USING fts5(title, body, grams, tokenize='unicode61')")
rows = [
    ('HBM4 量产节奏提前', '三星与 SK 海力士推进 HBM4，先进封装产能继续吃紧。'),
    ('存储芯片报价上调', 'DRAM 合约价上涨，AI 服务器需求支撑内存涨价。'),
]
for title, body in rows:
    conn.execute('INSERT INTO docs(title, body, grams) VALUES (?, ?, ?)', (title, body, grams(title + body)))
for q in ['HBM4', '内存', '存储芯片', '涨价', '先进封装', 'AI服务器']:
    gram_query = ' OR '.join(grams(q).split()[:8]) or q
    result = list(conn.execute('SELECT title FROM docs WHERE docs MATCH ? ORDER BY rank', (gram_query,)))
    print(q, gram_query, len(result), [r[0] for r in result])
'@ | uv run python -
```

输出摘要：

```text
HBM4 hb OR bm OR m4 OR hbm OR bm4 1 ['HBM4 量产节奏提前']
内存 内存 1 ['存储芯片报价上调']
存储芯片 存储 OR 储芯 OR 芯片 OR 存储芯 OR 储芯片 1 ['存储芯片报价上调']
涨价 涨价 1 ['存储芯片报价上调']
先进封装 先进 OR 进封 OR 封装 OR 先进封 OR 进封装 1 ['HBM4 量产节奏提前']
AI服务器 ai OR i服 OR 服务 OR 务器 OR ai服 OR i服务 OR 服务器 1 ['存储芯片报价上调']
```

后续约束：

```text
P2 可以创建 raw_document_fts 和 event_fts，但不要声称 unicode61 已解决中文召回。
P7 新增检索 Repository 时应增加 grams 字段或独立 ngram FTS 表，并用 tests/fixtures/event_insight/chinese_search_samples.json 回归。
```

## 5. Neo4j 验证

当前环境命令：

```powershell
docker --version
```

输出摘要：

```text
The term 'docker' is not recognized as a name of a cmdlet, function, script file, or executable program.
```

建议的 Neo4j Community 启动命令：

```powershell
docker run --name trendinsight-neo4j `
  -p 7474:7474 -p 7687:7687 `
  -e NEO4J_AUTH=neo4j/trendinsight-dev `
  -e NEO4J_dbms_security_procedures_unrestricted=gds.* `
  neo4j:5-community
```

P9 需要的环境变量：

```text
EVENT_INSIGHT_NEO4J_URI=bolt://localhost:7687
EVENT_INSIGHT_NEO4J_USER=neo4j
EVENT_INSIGHT_NEO4J_PASSWORD=trendinsight-dev
EVENT_INSIGHT_NEO4J_DATABASE=neo4j
```

后续约束：

```text
SQLite 是事实主库，Neo4j 只是可重建关系投影。
Neo4j 未配置或不可用时，事件列表和主题溯源必须继续可用。
关系图 API 应返回明确的 degraded 状态或 503 依赖不可用错误，前端展示降级提示。
P9 再引入 Neo4j 驱动和投影 Repository。
```

## 6. 前端图谱库选择

依赖检查命令：

```powershell
@'
const fs = require('fs');
const lock = JSON.parse(fs.readFileSync('frontend/package-lock.json', 'utf8'));
for (const name of ['node_modules/echarts', 'node_modules/zrender']) {
  const item = lock.packages[name];
  console.log(name, item ? item.version : 'missing');
}
console.log('has cytoscape', Boolean(lock.packages['node_modules/cytoscape']));
console.log('has g6', Boolean(lock.packages['node_modules/@antv/g6']));
console.log('has reactflow', Boolean(lock.packages['node_modules/reactflow'] || lock.packages['node_modules/@xyflow/react']));
'@ | node -
```

输出摘要：

```text
node_modules/echarts 6.0.0
node_modules/zrender 6.0.0
has cytoscape false
has g6 false
has reactflow false
```

候选结论：

```text
ECharts graph series：
  已在项目中使用，无新增 bundle 成本；支持 force layout、roam、节点/边点击、tooltip 和自定义样式。
  第一阶段足够承载 bounded topic subgraph。

Cytoscape.js：
  图谱交互能力更强，但需要新增依赖和样式整合；P9 只有在路径编辑/复杂布局明显超出 ECharts 时再评估。

AntV G6：
  能力完整但依赖体积和定制成本更高；当前项目无 AntV 体系，不作为第一选择。

React Flow / @xyflow/react：
  更适合流程编排而不是事件关系网络；不作为事件图谱第一选择。
```

后续约束：

```text
P9 优先实现 ECharts SVG 渲染的 topic subgraph。
图谱必须限制主题范围、时间范围和 maxDepth，避免一次渲染全库。
如果 ECharts 交互不足，再以独立增量引入 Cytoscape.js。
```

## 7. LLM 统一路径

现状：

```text
src/llm_providers/base_provider.py 定义 BaseLLMProvider。
src/llm_providers/openai_provider.py 使用 OpenAI SDK。
src/llm_providers/deepseek_provider.py 已经通过 OpenAI-compatible base_url 调 DeepSeek。
src/providers/live_data.py 中 ArkResearchProvider 直接创建 OpenAI(api_key, base_url) 客户端，用于现有未来事件日历研究补充。
```

迁移顺序：

```text
1. P5 扩展 BaseLLMProvider：base_url、timeout、structured output、embedding。
2. P5 新增 OpenAICompatibleProvider，覆盖 OpenAI、DeepSeek、Ark 和其他兼容供应商。
3. P5 新增 LlmTaskRouter，按 task_type 路由到 provider/model。
4. P5 先让 ArkResearchProvider 通过统一 client factory 构建客户端，但保持现有 Outlook 返回契约不变。
5. P6 事件抽取、P8 主题摘要、P9 关系判断必须只通过 LlmTaskRouter 调用模型。
```

安全约束：

```text
API Key 加密保存。
列表和编辑接口只返回脱敏 key。
日志禁止输出 API Key、完整请求头和完整 prompt。
LLM 响应必须写 llm_call_log，但只保存可审计摘要、任务类型、模型、耗时、状态和错误码。
```

## 8. P0 验收

静态日历基线命令：

```powershell
uv run python -m pytest tests/test_event_outlook_timeline.py -q
```

已观察结果：

```text
8 passed, 8 warnings
```

P0 完成前已在本分支重新运行：

```powershell
uv run python -m pytest -q
cmd /c npm --prefix frontend run test -- --run
cmd /c npm --prefix frontend run build
```

已观察结果：

```text
uv run python -m pytest -q
  108 passed, 120 warnings, 17 subtests passed

cmd /c npm --prefix frontend run test -- --run
  14 passed, 52 passed

cmd /c npm --prefix frontend run build
  built successfully; existing chunk-size warning remains for assets/index-BD1zC5wv.js
```

## 9. 后续包约束

```text
P2：创建 .data/event_insight.db、migration 和 FTS 表，但不引入 sqlite-vec。
P3：导入任务只写 SQLite 和本地文件，不触发 LLM 抽取。
P5：统一 LLM runtime，不添加事件抽取 prompt。
P7：再引入 sqlite-vec、embedding 表和 n-gram 检索回归。
P9：Neo4j 可选，SQLite outbox 是事实同步边界，ECharts 是第一版图谱渲染方案。
```
