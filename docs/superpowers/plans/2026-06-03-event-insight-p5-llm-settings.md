# Event Insight P5 LLM Runtime And Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付统一 LLM Runtime 与 Settings > 大模型配置，让后续 P6/P8/P9 只通过任务路由调用模型。

**Architecture:** SQLite 仍是本地事实与配置源；`llm_config_repository` 负责表读写，`llm_config_service` 负责脱敏、加密、禁用保护与连接测试，`llm_task_router` 负责按 task_type 选 provider。前端 Settings 使用 `/api/system/llm/*`，不展示明文密钥。

---

## 1. Backend

- [x] Write red tests for encrypted provider settings, task routing, disable conflict, and API redaction.
- [x] Add `002_llm_runtime` migration with provider/task/call-log tables.
- [x] Add local secret cipher, repository, config service, task router, and OpenAI-compatible provider.
- [x] Register `/api/system/llm/*` routes and inject service in FastAPI app.
- [x] Adapt ArkResearchProvider to OpenAI-compatible factory while preserving Event Outlook output contract.
- [x] Run backend focused gate:

```powershell
uv run python -m pytest tests/test_llm_task_router.py tests/test_llm_settings_api.py tests/test_event_outlook_timeline.py -q
```

## 2. Frontend

- [x] Write red Settings test for real provider list, redacted key, task mappings, save and connection test.
- [x] Add Settings API adapters/hooks/components.
- [x] Replace mock-only LLM workspace with query-backed UI.
- [x] Run frontend focused gate:

```powershell
cmd /c npm --prefix frontend run test -- src/features/settings/__tests__/settings-page.test.tsx --run
```

## 3. Docs And Commit

- [x] Update `docs/api-contract.md`, `docs/architecture.md`, `docs/test-strategy.md`, and `CHANGELOG.md`.
- [x] Run full backend/frontend/build gate.
- [ ] Commit as `feat: add task-routed llm settings`.

## 4. Stop Condition

P5 ends when providers and task mappings are persisted, redacted, testable, and routable. No event extraction prompt or extraction job processing is added in this package.
