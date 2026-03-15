# Task 01 Module Mapping

## Runtime Entrypoints

- Current: `main.py`
- Target Web entry: `src/app/web`
- Target job entry: `src/app/jobs`
- Target CLI entry: `src/app/cli`

## Current To Target Mapping

| Current | Problem | Target |
| --- | --- | --- |
| `main.py` | 入口和业务强耦合 | `src/app/jobs` + `src/services` |
| `src/news/fetcher.py` | 只适配当前 RSS 脚本流 | `src/providers/news_*` |
| `src/news/generator.py` | 抓取、选择、总结耦合 | `src/services/report_service.py` + `src/providers/llm_*` |
| `src/notifiers/*` | 与主流程直接耦合 | `src/delivery/*` |
| `src/llm_providers/*` | 当前命名仅覆盖 LLM，不利于统一 provider 分层 | `src/providers/llm_*` |
| `src/config.py` | 配置读取与应用层直接耦合 | `src/services/settings_service.py` 或后续 settings 模块 |

## Notes

- 当前阶段只建立边界，不移动现有实现文件。
- 迁移采用“包裹旧模块、逐步替换”的方式，避免一次性重写。
