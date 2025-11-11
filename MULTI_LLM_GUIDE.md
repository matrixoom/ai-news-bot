# 多LLM模型支持指南 / Multi-LLM Provider Guide

本项目现在支持多种LLM提供商，可以灵活切换使用 **Claude** 或 **DeepSeek**。

This project now supports multiple LLM providers, allowing you to switch between **Claude** and **DeepSeek**.

---

## 🎯 支持的模型 / Supported Providers

### 1. **Claude (Anthropic)** 
- **优势 / Advantages**: 
  - 顶级的文本理解和生成质量
  - Excellent text understanding and generation quality
  - 原项目默认模型，经过充分测试
  - Default model, thoroughly tested
  
- **默认模型 / Default Model**: `claude-sonnet-4-5-20250929`
- **其他可用模型 / Other Available Models**:
  - `claude-3-5-sonnet-20241022` (Sonnet 3.5)
  - `claude-haiku-4-5-20251001` (更快更便宜 / Faster & cheaper)
  - `claude-opus-4-1-20250805` (最强大 / Most powerful)

- **定价 / Pricing** (per million tokens):
  - Sonnet 4.5: $3 input / $15 output
  - Haiku 4.5: $1 input / $5 output

### 2. **DeepSeek** ⭐ 新增 / NEW
- **优势 / Advantages**:
  - 成本极低（比Claude便宜约90%）
  - Much lower cost (about 90% cheaper than Claude)
  - 对中文支持更好
  - Better Chinese language support
  - 性能优秀，适合新闻摘要任务
  - Excellent performance for news summarization
  
- **默认模型 / Default Model**: `deepseek-chat`
- **其他可用模型 / Other Available Models**:
  - `deepseek-reasoner` (推理增强版 / Enhanced reasoning)

- **定价 / Pricing** (per million tokens):
  - Input: $0.27 (~¥2)
  - Output: $1.10 (~¥8)
  - Cache hits: $0.014 (~¥0.1)

---

## 📝 配置方法 / Configuration

有两种配置方式 / There are two ways to configure:

### 方法1: 配置文件 / Method 1: Config File (推荐 / Recommended)

编辑 `config.yaml`:

```yaml
llm:
  # 选择提供商 / Choose provider: 'claude' or 'deepseek'
  provider: deepseek
  
  # 可选：指定具体模型 / Optional: Specify model
  model: deepseek-chat
```

**切换到Claude / Switch to Claude:**
```yaml
llm:
  provider: claude
  # model: claude-sonnet-4-5-20250929  # 可选
```

**切换到DeepSeek / Switch to DeepSeek:**
```yaml
llm:
  provider: deepseek
  # model: deepseek-chat  # 可选
```

### 方法2: 环境变量 / Method 2: Environment Variables

在 `.env` 文件中设置（优先级高于config.yaml）:

```bash
# 选择提供商 / Choose provider
LLM_PROVIDER=deepseek

# 可选：指定模型 / Optional: Specify model
LLM_MODEL=deepseek-chat
```

或在GitHub Actions中设置 / Or set in GitHub Actions:
- 添加 Repository Secret: `LLM_PROVIDER` = `deepseek`
- 添加 Repository Secret: `LLM_MODEL` = `deepseek-chat` (可选)

---

## 🔑 API密钥配置 / API Key Configuration

### 使用Claude时 / When using Claude:

在 `.env` 中设置:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxx...
```

或在GitHub Actions中添加Secret:
- Secret名称: `ANTHROPIC_API_KEY`
- Secret值: 你的Claude API密钥

**获取密钥 / Get API Key**: https://console.anthropic.com/

### 使用DeepSeek时 / When using DeepSeek:

在 `.env` 中设置:
```bash
DEEPSEEK_API_KEY=sk-xxx...
```

或在GitHub Actions中添加Secret:
- Secret名称: `DEEPSEEK_API_KEY`
- Secret值: 你的DeepSeek API密钥

**获取密钥 / Get API Key**: https://platform.deepseek.com/

---

## 💡 使用示例 / Usage Examples

### 示例1: 本地开发使用DeepSeek / Example 1: Local Development with DeepSeek

1. 编辑 `config.yaml`:
```yaml
llm:
  provider: deepseek
```

2. 编辑 `.env`:
```bash
DEEPSEEK_API_KEY=sk-your-key-here
AI_RESPONSE_LANGUAGE=zh
NOTIFICATION_METHODS=email
```

3. 运行:
```bash
python main.py
```

### 示例2: GitHub Actions使用Claude / Example 2: GitHub Actions with Claude

1. `config.yaml` 保持默认:
```yaml
llm:
  provider: claude
```

2. 在GitHub Repository中设置Secrets:
- `ANTHROPIC_API_KEY`: 你的API密钥
- `NOTIFICATION_METHODS`: `email`
- `EMAIL_FROM`: ...
- `EMAIL_TO`: ...

### 示例3: 环境变量覆盖配置文件 / Example 3: Override with Environment Variables

即使 `config.yaml` 设置为 `claude`，也可以通过环境变量切换:

```bash
# .env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-key-here
```

这样无需修改配置文件即可切换模型。

---

## 🎨 功能兼容性 / Feature Compatibility

| 功能 / Feature | Claude | DeepSeek |
|----------------|--------|----------|
| 基础新闻生成 / Basic news generation | ✅ | ✅ |
| RSS源摘要 / RSS feed summarization | ✅ | ✅ |
| 多语言支持 / Multi-language | ✅ | ✅ |
| Web搜索工具 / Web search tool | ✅ | ✅ |
| 邮件通知 / Email notification | ✅ | ✅ |
| Webhook通知 / Webhook | ✅ | ✅ |

两个提供商支持所有功能！/ Both providers support all features!

---

## 📊 性能对比 / Performance Comparison

**新闻摘要任务 / News Summarization Task:**

| 维度 / Metric | Claude Sonnet 4.5 | DeepSeek |
|---------------|-------------------|----------|
| 质量 / Quality | ⭐⭐⭐⭐⭐ (9.5/10) | ⭐⭐⭐⭐⭐ (9/10) |
| 速度 / Speed | 快 / Fast | 很快 / Very Fast |
| 成本 / Cost | 高 / High | 极低 / Very Low |
| 中文能力 / Chinese | 优秀 / Excellent | 卓越 / Outstanding |
| 英文能力 / English | 卓越 / Outstanding | 优秀 / Excellent |

**建议 / Recommendations:**
- 🏢 **企业用户**: 预算充足 → Claude
- 💰 **个人用户**: 关注成本 → DeepSeek  
- 🇨🇳 **中文用户**: 推荐 DeepSeek
- 🌍 **英文用户**: 两者都很好
- 🧪 **测试阶段**: 推荐 DeepSeek (省钱)

---

## 🔧 技术架构 / Technical Architecture

项目使用**策略模式**实现多provider支持:

```
src/llm_providers/
├── __init__.py              # Provider工厂函数
├── base_provider.py         # 抽象基类
├── claude_provider.py       # Claude实现
└── deepseek_provider.py     # DeepSeek实现
```

**核心接口 / Core Interface:**
```python
class BaseLLMProvider(ABC):
    def generate(messages, max_tokens, ...) -> str
    def generate_with_tools(messages, tools, ...) -> str
```

两个提供商实现相同的接口，因此可以无缝切换。

---

## ❓ 常见问题 / FAQ

### Q1: 我可以同时使用两个模型吗？
**A**: 目前不支持，但可以通过切换配置快速更换。未来版本可能支持负载均衡。

### Q2: DeepSeek的质量真的够用吗？
**A**: 是的！对于新闻摘要这种任务，DeepSeek的表现非常好，特别是中文内容。

### Q3: 切换模型需要修改代码吗？
**A**: 不需要！只需修改配置文件或环境变量即可。

### Q4: 如何测试不同模型的效果？
**A**: 可以多次运行，每次使用不同的provider配置，对比输出结果。

### Q5: Tool calling (Web搜索) 在DeepSeek上工作吗？
**A**: 是的，DeepSeek支持OpenAI格式的function calling，项目已做好适配。

---

## 🚀 快速切换指南 / Quick Switch Guide

### 从Claude切换到DeepSeek:

1. 修改 `config.yaml`:
```yaml
llm:
  provider: deepseek  # claude → deepseek
```

2. 添加API密钥到 `.env`:
```bash
DEEPSEEK_API_KEY=sk-xxx...
```

3. 运行测试:
```bash
python main.py
```

### 从DeepSeek切换回Claude:

1. 修改 `config.yaml`:
```yaml
llm:
  provider: claude  # deepseek → claude
```

2. 确保API密钥在 `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-xxx...
```

3. 运行测试:
```bash
python main.py
```

---

## 📞 支持 / Support

如有问题，请提交GitHub Issue或查看以下资源:

- Claude文档: https://docs.anthropic.com/
- DeepSeek文档: https://platform.deepseek.com/docs
- 项目README: [README.md](README.md)

---

**版本 / Version**: 2.0  
**更新日期 / Last Updated**: 2025-11-11
