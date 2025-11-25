<div align="center">

# AI 新闻机器人

🤖 **您的 AI 新闻助手** — 每日自动获取个性化 AI 新闻摘要，保持信息灵通

[![GitHub Stars](https://img.shields.io/github/stars/giftedunicorn/ai-news-bot?style=flat-square&logo=github&color=yellow)](https://github.com/giftedunicorn/ai-news-bot/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/giftedunicorn/ai-news-bot?style=flat-square&logo=github&color=blue)](https://github.com/giftedunicorn/ai-news-bot/network/members)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)

[![邮件](https://img.shields.io/badge/邮件-通知-00D4AA?style=flat-square)](https://resend.com/)
[![Webhook](https://img.shields.io/badge/Webhook-支持-00D4AA?style=flat-square)](#)
[![Slack](https://img.shields.io/badge/Slack-集成-00D4AA?style=flat-square)](https://slack.com/)
[![Telegram](https://img.shields.io/badge/Telegram-机器人-00D4AA?style=flat-square)](https://telegram.org/)

[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-自动化-2088FF?style=flat-square&logo=github-actions&logoColor=white)](https://github.com/giftedunicorn/ai-news-bot)
[![Claude](https://img.shields.io/badge/Claude-Sonnet_4.5-FF6B6B?style=flat-square&logo=anthropic&logoColor=white)](https://www.anthropic.com)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-支持-4285F4?style=flat-square&logo=ai&logoColor=white)](https://www.deepseek.com)

</div>

---

## 📑 快速导航

<div align="center">

| [✨ 功能特点](#功能特点) | [🚀 快速开始](#快速开始本地开发) | [⚙️ 配置](#配置) | [🤖 LLM 提供商](#llm-提供商配置) |
|:---:|:---:|:---:|:---:|
| [🌍 语言配置](#语言配置) | [📧 邮件设置](#resendcom-邮件设置指南) | [🔗 Webhook](#webhook-集成) | [🔧 故障排除](#故障排除) |

</div>

---

## 功能特点

- **多 LLM 提供商支持**：可选择 Claude (Anthropic) 或 DeepSeek 进行新闻生成
- **实时新闻获取**：从 RSS 源获取真实新闻，确保内容准确、及时
- **AI 驱动的新闻生成**：使用 Claude Sonnet 4.5 或 DeepSeek 生成全面的 AI 新闻摘要
- **网络搜索集成**：可选的 DuckDuckGo 网络搜索，获取更多新闻来源
- **精美的邮件格式**：自动将 AI 内容转换为精美的 HTML 邮件 - 无 markdown，只有简洁专业的设计
- **可定制的提示词**：9 个预设模板（综合、研究、商业、技术等）或创建自定义模板
- **多语言支持**：支持 13+ 种语言生成新闻，包括中文、英文、西班牙语、法语、日语等
- **中文新闻源支持**：内置中文 AI 新闻源支持（36氪、机器之心等）
- **多通知渠道**：支持邮件（通过 Resend.com）和 Webhook 通知
- **灵活配置**：通过 YAML 配置文件轻松自定义主题和通知设置
- **自动调度**：GitHub Actions 工作流支持每日自动执行
- **健壮的错误处理**：全面的日志记录和重试逻辑
- **邮件客户端兼容**：完美支持 Gmail、Outlook、Apple Mail 和移动邮件应用
- **现代邮件投递**：使用 Resend.com 实现可靠、开发者友好的邮件投递

## 🚀 部署选项

选择您的部署方式：

| 方式 | 配置方法 | 使用场景 |
|------|---------|---------|
| **本地开发** | `.env` 文件 | 在本地计算机上测试 |
| **GitHub Actions** | 仓库 Secrets | 自动化每日运行（推荐）|

> 💡 **提示**：先在本地开发环境测试，然后部署到 GitHub Actions 实现自动化。

## 快速开始（本地开发）

### 1. 克隆仓库

```bash
git clone <your-repo-url>
cd ai-news-bot
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置设置（本地开发）

对于**本地开发**，复制示例文件并填入您的凭证：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入实际值：

```env
# LLM 提供商配置
LLM_PROVIDER=claude  # 可选：'claude' 或 'deepseek'

# API 密钥（根据使用的提供商填写）
ANTHROPIC_API_KEY=your_api_key_here      # Claude 使用
DEEPSEEK_API_KEY=your_deepseek_api_key   # DeepSeek 使用

# 可选：Resend.com 邮件配置
RESEND_API_KEY=re_your_api_key_here
EMAIL_FROM=your_email@yourdomain.com
EMAIL_TO=recipient@example.com

# 可选：Webhook 配置
WEBHOOK_URL=https://your-webhook-url.com/endpoint

# 通知方式（逗号分隔）
NOTIFICATION_METHODS=email,webhook

# 语言设置（可选，默认为 'en'）
AI_RESPONSE_LANGUAGE=zh

# 网络搜索（可选，默认为 false）
ENABLE_WEB_SEARCH=false
```

> **注意**：`.env` 文件仅用于**本地开发**。对于 GitHub Actions 自动化，您需要将这些配置为 **GitHub Secrets**（参见下方 [GitHub Actions 设置](#github-actions-设置)）。

### 4. 自定义新闻提示词（可选）

机器人使用**优化的简洁提示词**（15行 vs 典型系统的 50+ 行）生成高质量的新闻摘要。

**默认提示词**（在 config.yaml 中）：
```yaml
Summarize 10 recent AI news items (5 international + 5 domestic) covering: {topics}

Format:
International News:
1. [Headline]
[2-3 sentence summary]
Source: [Name]

Domestic News:
1. [Headline]
...

Rules: Recent news, no markdown, clear language
```

**为何简洁：**
- ✅ 处理更快
- ✅ 成本更低
- ✅ 更易维护
- ✅ 无冗余

**多语言支持：**

提示词使用英文（最适合 Claude），但输出可以是 **13+ 种语言**：
```bash
# 在 .env 文件中
AI_RESPONSE_LANGUAGE=zh  # 中文输出
AI_RESPONSE_LANGUAGE=es  # 西班牙语输出
AI_RESPONSE_LANGUAGE=ja  # 日语输出
# 支持：en, zh, es, fr, ja, de, ko, pt, ru, ar, hi, it, nl
```

**预设模板**（config.examples.yaml）：
1. 综合（默认）- 均衡覆盖
2. 研究 - 学术焦点
3. 商业 - 行业与融资
4. 技术 - 工程深度
5. 创业 - 早期公司
6. 政策 - 法规
7. 周报 - 热门故事
8. 简洁 - 超简短
9. 中文 - 中文示例

📖 **完整指南**：参见 `config.examples.yaml` 了解自定义和多语言详情。

### 5. 本地运行

```bash
python main.py
```

## 配置

### 配置变量

机器人需要以下配置。设置方式取决于您的部署环境：

- **本地开发**：使用 `.env` 文件（参见[快速开始](#快速开始本地开发)）
- **GitHub Actions**：使用 GitHub 仓库 Secrets（参见 [GitHub Actions 设置](#github-actions-设置)）

| 变量 | 是否必需 | 描述 |
|------|---------|------|
| `LLM_PROVIDER` | 可选 | LLM 提供商：`claude` 或 `deepseek`（默认：`claude`）|
| `ANTHROPIC_API_KEY` | 使用 Claude 时需要 | 您的 Anthropic API 密钥 |
| `DEEPSEEK_API_KEY` | 使用 DeepSeek 时需要 | 您的 DeepSeek API 密钥 |
| `NOTIFICATION_METHODS` | ✅ 必需 | 逗号分隔的列表：`email`、`webhook` 或 `email,webhook` |
| `AI_RESPONSE_LANGUAGE` | 可选 | AI 响应的语言代码（默认：`en`）。支持：`zh`、`es`、`fr`、`ja`、`de`、`ko`、`pt`、`ru`、`ar`、`hi`、`it`、`nl` |
| `ENABLE_WEB_SEARCH` | 可选 | 启用网络搜索获取新闻（默认：`false`）|
| `RESEND_API_KEY` | 使用邮件时需要 | 您的 Resend.com API 密钥 |
| `EMAIL_FROM` | 使用邮件时需要 | 发件人邮箱地址（必须在 Resend 中验证）|
| `EMAIL_TO` | 使用邮件时需要 | 收件人邮箱地址 |
| `WEBHOOK_URL` | 使用 webhook 时需要 | Webhook 端点 URL |

### 配置文件（config.yaml）

`config.yaml` 文件允许您自定义新闻摘要行为：

**LLM 配置**：
- **Provider（提供商）**：选择 `claude` 或 `deepseek`
- **Model（模型）**：可选指定特定模型版本

**新闻配置**：
- **use_real_sources**：启用从 RSS 源获取新闻（推荐，默认：true）
- **enable_web_search**：启用 DuckDuckGo 网络搜索（默认：false）
- **include_chinese_sources**：包含中文新闻源（默认：true）
- **max_items_per_source**：每个源的最大新闻条目数（默认：10）
- **Topics（主题）**：新闻选择的焦点领域（可选，引导 AI）
- **Prompt Template（提示词模板）**：LLM 的指令模板
  - 默认：综合 15-20 条新闻摘要，带分类标题
  - 可完全自定义提示词
  - 参见 `config.examples.yaml` 中的 9 个预设模板

**日志设置**：控制日志详细程度和格式

**示例结构**：
```yaml
llm:
  provider: claude  # 或 'deepseek'
  # model: claude-sonnet-4-5-20250929  # 可选

news:
  use_real_sources: true
  enable_web_search: false
  include_chinese_sources: true
  max_items_per_source: 10

  topics:
    - "大语言模型 (LLM)"
    - "AI 智能体和自主系统"
    - "产品发布"

  prompt_template: |
    您的自定义提示词...
    焦点：{topics}

logging:
  level: INFO
  format: "%(asctime)s - %(levelname)s - %(message)s"
```

### LLM 提供商配置

机器人支持多个 LLM 提供商。在 `config.yaml` 或环境变量中配置：

#### Claude (Anthropic) - 默认
```yaml
llm:
  provider: claude
  model: claude-sonnet-4-5-20250929  # 可选，未设置则使用默认值
```

**可用的 Claude 模型：**
- `claude-sonnet-4-5-20250929` - 最新 Sonnet（默认）- 最适合大多数任务
- `claude-3-5-sonnet-20241022` - 上一版本 Sonnet

**Claude 定价（每百万 token）：**
- Claude Sonnet 4.5：$3 输入 / $15 输出

#### DeepSeek - 高性价比替代方案
```yaml
llm:
  provider: deepseek
  model: deepseek-chat  # 可选，未设置则使用默认值
```

**可用的 DeepSeek 模型：**
- `deepseek-chat` - 通用聊天模型（默认）
- `deepseek-reasoner` - 增强推理模型

**DeepSeek 定价：**
- 成本远低于 Claude
- 更好的中文语言支持
- 新闻摘要质量良好

#### 选择提供商

| 提供商 | 优点 | 缺点 | 最适合 |
|--------|------|------|--------|
| **Claude** | 质量优秀，可靠 | 成本较高 | 生产环境，高质量输出 |
| **DeepSeek** | 成本低，中文好 | 质量略低 | 预算有限，中文内容 |

### 语言配置

**工作原理：**
- 提示词始终使用**英文**（最适合 Claude 理解）
- 输出可以是 **13+ 种语言**（自动翻译）
- 在 `.env` 或 GitHub Secrets 中设置 `AI_RESPONSE_LANGUAGE`

**支持的语言：**

`en`（English）• `zh`（中文）• `es`（Español）• `fr`（Français）• `ja`（日本語）• `de`（Deutsch）• `ko`（한국어）• `pt`（Português）• `ru`（Русский）• `ar`（العربية）• `hi`（हिन्दी）• `it`（Italiano）• `nl`（Nederlands）

**使用方法：**

```bash
# .env 文件
AI_RESPONSE_LANGUAGE=zh  # 完整中文输出

# GitHub Secret
# 添加：AI_RESPONSE_LANGUAGE = zh
```

**示例输出（中文）：**
```
国际新闻：

1. OpenAI发布GPT-5增强推理能力
OpenAI发布了GPT-5...
来源：OpenAI官方博客
```

系统会自动添加："IMPORTANT: Please respond entirely in Chinese (中文)" 到提示词中。

## GitHub Actions 设置

项目包含一个 GitHub Actions 工作流，默认在每天 UTC 时间 00:00（北京时间 08:00）运行。

> **重要**：GitHub Actions 使用**仓库 Secrets** 进行配置（不是环境变量）。所有设置都必须添加为 secrets。

### 步骤 1：添加 GitHub 仓库 Secrets

导航到您的 GitHub 仓库：

```
仓库 → Settings → Secrets and variables → Actions → Repository secrets → New repository secret
```

逐个添加以下 secrets：

#### ✅ 必需的 Secrets

| Secret 名称 | 示例值 | 描述 |
|------------|--------|------|
| `LLM_PROVIDER` | `claude` 或 `deepseek` | LLM 提供商（默认：`claude`）|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-xxx...` | 您的 Anthropic API 密钥（使用 Claude 时）|
| `DEEPSEEK_API_KEY` | `sk-xxx...` | 您的 DeepSeek API 密钥（使用 DeepSeek 时）|
| `NOTIFICATION_METHODS` | `email,webhook` | 通知渠道（逗号分隔）|

#### 📧 邮件 Secrets（如果使用邮件通知）

| Secret 名称 | 示例值 | 描述 |
|------------|--------|------|
| `RESEND_API_KEY` | `re_123abc...` | 您的 Resend.com API 密钥 |
| `EMAIL_FROM` | `news@yourdomain.com` | 发件人邮箱（必须在 Resend 中验证）|
| `EMAIL_TO` | `you@example.com` | 收件人邮箱地址 |

#### 🔗 Webhook Secrets（如果使用 webhook 通知）

| Secret 名称 | 示例值 | 描述 |
|------------|--------|------|
| `WEBHOOK_URL` | `https://hooks.slack.com/...` | 您的 webhook 端点 URL |

#### 🌍 可选的 Secrets

| Secret 名称 | 示例值 | 描述 |
|------------|--------|------|
| `AI_RESPONSE_LANGUAGE` | `zh` 或 `es` 或 `ja` | 语言代码（未设置时默认为 `en`）|
| `ENABLE_WEB_SEARCH` | `true` 或 `false` | 启用网络搜索获取新闻（默认为 `false`）|

### 步骤 2：启用 GitHub Actions

确保在仓库设置中启用了 GitHub Actions：

```
仓库 → Settings → Actions → General → Allow all actions and reusable workflows
```

### 步骤 3：手动触发（测试设置）

配置好 secrets 后，测试您的设置：

```
仓库 → Actions 标签 → Daily AI News Digest → Run workflow 按钮
```

这将立即运行工作流，以便您验证一切正常工作。

### 步骤 4：自定义调度（可选）

工作流默认在每天 UTC 时间午夜运行。要更改调度，编辑 `.github/workflows/daily-news.yml`：

```yaml
schedule:
  - cron: '0 0 * * *'  # 每天 UTC 午夜（当前）
  - cron: '0 9 * * *'  # 每天 UTC 9:00
  - cron: '0 */6 * * *'  # 每 6 小时
```

使用 [crontab.guru](https://crontab.guru/) 创建自定义调度。

## 项目结构

```
ai-news-bot/
├── .github/
│   └── workflows/
│       └── daily-news.yml           # GitHub Actions 工作流
├── src/
│   ├── __init__.py
│   ├── config.py                    # 配置管理
│   ├── logger.py                    # 日志工具
│   ├── news_generator.py            # 新闻生成编排
│   ├── news_fetcher.py              # RSS 源新闻获取
│   ├── web_search.py                # DuckDuckGo 网络搜索集成
│   ├── llm_providers/
│   │   ├── __init__.py
│   │   ├── base_provider.py         # LLM 提供商基础接口
│   │   ├── claude_provider.py       # Anthropic Claude 提供商
│   │   └── deepseek_provider.py     # DeepSeek 提供商
│   └── notifiers/
│       ├── __init__.py
│       ├── email_notifier.py        # 邮件通知
│       └── webhook_notifier.py      # Webhook 通知
├── main.py                          # 主应用入口
├── config.yaml                      # 活动配置文件
├── requirements.txt                 # Python 依赖
├── .env.example                     # 示例环境变量
├── .gitignore
├── README.md
└── README.zh.md                     # 中文文档
```

## 使用示例

### 仅邮件

```env
NOTIFICATION_METHODS=email
```

### 仅 Webhook

```env
NOTIFICATION_METHODS=webhook
```

### 邮件和 Webhook

```env
NOTIFICATION_METHODS=email,webhook
```

## 邮件格式

### 精美的邮件友好设计

机器人生成**邮件优化的内容**，在所有邮件客户端中都显示精美：

**功能：**
- ✅ 无 markdown 格式（简洁、专业的外观）
- ✅ 自动 HTML 转换，带精美样式
- ✅ 带视觉徽章的编号新闻卡片
- ✅ 颜色编码的章节和标题
- ✅ 移动端响应式布局
- ✅ 支持 Gmail、Outlook、Apple Mail 和所有移动应用

**收件人看到的：**
- 带专业样式的简洁白色容器
- 带微妙边框的蓝色章节标题
- 样式化卡片中的编号新闻项
- 斜体来源引用
- 在任何设备上都舒适的阅读体验

**预览您的邮件：**
在本地运行机器人并检查生成的 HTML 邮件内容。

## Resend.com 邮件设置指南

### 设置 Resend

1. **注册 Resend**
   - 访问 [resend.com](https://resend.com) 并创建账户
   - Resend 提供慷慨的免费额度（每天100封邮件，每月3,000封邮件）

2. **获取 API 密钥**
   - 在 Resend 仪表板中导航到 API Keys
   - 创建新的 API 密钥
   - 复制 API 密钥（以 `re_` 开头）并设置为 `RESEND_API_KEY`

3. **验证您的域名**（生产环境推荐）
   - 在 Resend 仪表板中转到 Domains
   - 通过添加 DNS 记录来添加和验证您的域名
   - 验证后，您可以从域名下的任何地址发送邮件

4. **测试用途**（无需域名验证）
   - 您可以使用 `onboarding@resend.dev` 作为 `EMAIL_FROM` 地址
   - 这仅用于测试，有发送限制
   - 生产使用请验证您自己的域名

### 为什么选择 Resend？

- **简单的 API**：易于使用的 REST API，比 SMTP 简单得多
- **更好的投递率**：更高的收件箱到达率
- **无 SMTP 配置**：无需管理 SMTP 凭证
- **现代化**：为开发者构建，文档出色
- **分析**：跟踪邮件投递和参与度

## Webhook 集成

Webhook 发送 JSON 负载：

```json
{
  "title": "AI News Digest - 2025-10-25",
  "content": "... 新闻摘要内容 ...",
  "timestamp": "2025-10-25T09:00:00",
  "source": "AI News Bot"
}
```

兼容：
- Slack（使用 Incoming Webhooks）
- Discord（使用 Webhook URLs）
- Microsoft Teams
- 自定义 webhook 端点

## 错误处理

- **自动重试**：新闻生成器在失败时最多重试 3 次
- **优雅降级**：如果一种通知方式失败，其他方式仍会执行
- **全面日志**：所有操作都带有时间戳和上下文记录
- **GitHub Actions 工件**：上传错误日志以便调试

## 故障排除

### "Config file not found" 错误

确保 `config.yaml` 存在于项目根目录。

### 邮件未发送

- 验证 `RESEND_API_KEY` 正确且有效
- 确保 `EMAIL_FROM` 在 Resend 中已验证（或使用 `onboarding@resend.dev` 进行测试）
- 检查 Resend 仪表板的投递日志和错误
- 验证您没有超过 Resend 的发送限制

### Webhook 失败

- 验证 webhook URL 可访问
- 检查 webhook 端点接受 JSON POST 请求
- 查看 webhook 服务日志

### API 错误

- 验证 `ANTHROPIC_API_KEY` 有效
- 检查 API 配额/速率限制
- 查看 Anthropic API 状态

## 开发

### 运行测试（如果可用）

```bash
pytest
```

### 本地开发

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows 上：venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行机器人
python main.py
```

## 许可证

MIT 许可证 - 详见 LICENSE 文件

## 支持

如有问题和功能请求，请使用 GitHub issue 跟踪器。

## 致谢

由以下技术提供支持：
- [Anthropic Claude](https://www.anthropic.com)
- [DeepSeek](https://www.deepseek.com)

---

## ⭐ Star 历史

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=giftedunicorn/ai-news-bot&type=Date)](https://star-history.com/#giftedunicorn/ai-news-bot&Date)

</div>

---

<div align="center">

**[⬆ 返回顶部](#ai-新闻机器人)**

用 ❤️ 由开源社区打造

</div>
