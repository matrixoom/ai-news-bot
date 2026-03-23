"""Push center service for configurable previews, delivery, and schedules."""
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
import re
import threading
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..notifiers import EmailNotifier
from .dashboard_service import DashboardService
from .push_report_service import PushReportService


logger = logging.getLogger(__name__)

SUPPORTED_CHANNEL_TYPES = (
    {
        "id": "email",
        "label": "邮箱",
        "enabled": True,
        "description": "SMTP 邮件推送，适合作为日报和定时推送首个渠道。",
    },
    {
        "id": "webhook",
        "label": "Webhook",
        "enabled": False,
        "description": "预留给后续渠道扩展。",
    },
)

AVAILABLE_SOURCE_MODULES = (
    {
        "id": "market",
        "label": "市场模型",
        "enabled": True,
        "push_ready": True,
        "description": "当前最适合日报推送的模块。",
    },
    {
        "id": "macro",
        "label": "宏观指标",
        "enabled": False,
        "push_ready": False,
        "description": "已预留扩展位，暂不推荐用于日报。",
    },
    {
        "id": "news",
        "label": "新闻情报",
        "enabled": False,
        "push_ready": False,
        "description": "已预留扩展位，暂不推荐用于日报。",
    },
    {
        "id": "events",
        "label": "事件展望",
        "enabled": False,
        "push_ready": False,
        "description": "已预留扩展位，暂不推荐用于日报。",
    },
)

STYLE_OPTIONS = (
    {
        "id": "newspaper",
        "label": "报刊双栏",
        "recommended": True,
        "description": "左右分栏，适合晨报和盘中快照。",
    },
    {
        "id": "briefing",
        "label": "简报单栏",
        "recommended": False,
        "description": "更紧凑，适合快速浏览。",
    },
)

DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_PUSH_CONFIG = {
    "selected_module_ids": ["market"],
    "report_style": "newspaper",
    "email": {
        "enabled": True,
        "label": "Primary Email",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "use_tls": True,
        "username": "",
        "password": "",
        "from_address": "",
        "to_addresses": "",
    },
    "schedules": [
        {
            "id": "market-daily",
            "name": "市场日报",
            "enabled": True,
            "module_ids": ["market"],
            "channel_types": ["email"],
            "times": ["08:00", "12:00", "17:00"],
            "timezone": DEFAULT_TIMEZONE,
        }
    ],
    "recent_runs": [],
    "scheduler_history": {},
}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class PushCenterService:
    """Owns push-center config, previews, manual delivery, and schedule execution."""

    def __init__(
        self,
        *,
        dashboard_service: DashboardService | None = None,
        report_service: PushReportService | None = None,
        config_path: str | Path | None = None,
        enable_scheduler: bool = False,
        scheduler_check_seconds: float | None = None,
        email_notifier_factory=EmailNotifier,
    ) -> None:
        self._dashboard_service = dashboard_service or DashboardService()
        self._report_service = report_service or PushReportService()
        self._email_notifier_factory = email_notifier_factory
        self._config_path = Path(
            config_path or os.getenv("PUSH_CENTER_CONFIG_PATH", ".data/push_center.json")
        )
        self._config_lock = threading.Lock()
        self._scheduler_check_seconds = max(
            5.0,
            float(
                scheduler_check_seconds
                if scheduler_check_seconds is not None
                else os.getenv("PUSH_CENTER_SCHEDULER_CHECK_SECONDS", "20")
            ),
        )
        self._scheduler_stop_event = threading.Event()
        self._scheduler_thread: threading.Thread | None = None
        self._ensure_config_file()
        if enable_scheduler:
            self.start_scheduler()

    def build_module_payload(self) -> dict[str, Any]:
        config = self._load_config()
        preview = self._build_preview(config)
        note = f"{len(config['schedules'])} 个任务 / {len(config['selected_module_ids'])} 个模块"
        return {
            "generated_at": _utc_now_iso(),
            "module": {
                "id": "push",
                "label": "推送中心",
                "note": note,
                "description": "配置邮件推送、预览日报样式，并管理定时任务。",
                "status": self._module_status(config, preview),
                "loading": False,
                "details": [
                    {
                        "id": "workspace",
                        "label": "推送配置",
                        "kind": "push",
                        "note": note,
                        "section": {
                            "channel_type_options": list(SUPPORTED_CHANNEL_TYPES),
                            "source_module_options": list(AVAILABLE_SOURCE_MODULES),
                            "style_options": list(STYLE_OPTIONS),
                            "config": self._public_config(config),
                            "preview": preview,
                            "recent_runs": list(config.get("recent_runs", [])),
                            "scheduler": {
                                "enabled": self._scheduler_thread is not None,
                                "check_interval_seconds": self._scheduler_check_seconds,
                            },
                        },
                    }
                ],
            },
        }

    def update_config(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        payload = self._unwrap_payload(payload)
        existing = self._load_config()
        normalized = self._normalize_config(payload or {}, base=existing)
        self._save_config(normalized)
        return self.build_module_payload()

    def build_preview_response(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        payload = self._unwrap_payload(payload)
        existing = self._load_config()
        normalized = self._normalize_config(payload or {}, base=existing)
        return {
            "generated_at": _utc_now_iso(),
            "config": self._public_config(normalized),
            "preview": self._build_preview(normalized),
        }

    def trigger_push(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = self._unwrap_payload(payload)
        existing = self._load_config()
        normalized = self._normalize_config(payload or {}, base=existing)
        persist = bool((payload or {}).get("persist"))
        result = self._execute_delivery(normalized, trigger="manual", job_name="手动触发")
        merged = deepcopy(existing)
        if persist:
            merged.update({k: deepcopy(v) for k, v in normalized.items() if k not in {"recent_runs", "scheduler_history"}})
        merged["recent_runs"] = list(result["recent_runs"])
        merged["scheduler_history"] = dict(existing.get("scheduler_history", {}))
        self._save_config(merged)
        return result

    def run_due_jobs(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        config = self._load_config()
        current_time = now or datetime.now(UTC)
        results: list[dict[str, Any]] = []
        dirty = False
        for schedule in config.get("schedules", []):
            if not schedule.get("enabled"):
                continue
            if not self._is_schedule_due(schedule, current_time, config):
                continue
            run_result = self._execute_delivery(
                config,
                trigger="scheduled",
                job_name=str(schedule.get("name") or "定时推送"),
                module_ids=schedule.get("module_ids") or config.get("selected_module_ids"),
                channel_types=schedule.get("channel_types") or ["email"],
            )
            schedule_key = self._schedule_history_key(schedule, current_time)
            config.setdefault("scheduler_history", {})[schedule_key] = run_result["result"]["executed_at"]
            config["recent_runs"] = list(run_result["recent_runs"])
            dirty = True
            results.append(run_result)
        if dirty:
            self._trim_scheduler_history(config)
            self._save_config(config)
        return results

    def start_scheduler(self) -> None:
        if self._scheduler_thread is not None:
            return
        self._scheduler_stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="push-center-scheduler",
            daemon=True,
        )
        self._scheduler_thread.start()

    def stop_scheduler(self) -> None:
        self._scheduler_stop_event.set()
        if self._scheduler_thread is not None:
            self._scheduler_thread.join(timeout=2.0)
            self._scheduler_thread = None

    def _scheduler_loop(self) -> None:
        while not self._scheduler_stop_event.wait(self._scheduler_check_seconds):
            try:
                self.run_due_jobs()
            except Exception as error:  # pragma: no cover - defensive background logging
                logger.warning("push-center scheduler loop failed: %s", error)

    def _build_preview(self, config: Mapping[str, Any], *, module_ids: Iterable[str] | None = None) -> dict[str, Any]:
        selected_modules = list(module_ids or config.get("selected_module_ids") or ["market"])
        try:
            snapshot = self._dashboard_service.build_snapshot()
            subject = self._build_subject(snapshot, config, selected_modules)
            text_body = self._report_service.build_markdown(snapshot, module_ids=selected_modules)
            html_body = self._report_service.build_email_html(
                snapshot,
                module_ids=selected_modules,
                layout=str(config.get("report_style") or "newspaper"),
            )
            return {
                "ok": True,
                "generated_at": snapshot.generated_at,
                "subject": subject,
                "text_body": text_body,
                "html_body": html_body,
                "style": config.get("report_style") or "newspaper",
                "selected_module_ids": selected_modules,
            }
        except Exception as error:
            return {
                "ok": False,
                "generated_at": _utc_now_iso(),
                "subject": "推送预览不可用",
                "text_body": "",
                "html_body": "",
                "style": config.get("report_style") or "newspaper",
                "selected_module_ids": selected_modules,
                "error": str(error),
            }

    def _build_subject(self, snapshot, config: Mapping[str, Any], module_ids: Iterable[str]) -> str:
        module_map = {item["id"]: item["label"] for item in AVAILABLE_SOURCE_MODULES}
        module_labels = [module_map[module_id] for module_id in module_ids if module_id in module_map]
        base = self._report_service.build_subject(snapshot)
        if module_labels:
            return f"{' / '.join(module_labels)} - {base}"
        return base

    def _execute_delivery(
        self,
        config: Mapping[str, Any],
        *,
        trigger: str,
        job_name: str,
        module_ids: Iterable[str] | None = None,
        channel_types: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        selected_modules = list(module_ids or config.get("selected_module_ids") or ["market"])
        selected_channels = [str(item).strip().lower() for item in (channel_types or ["email"]) if str(item).strip()]
        preview = self._build_preview(config, module_ids=selected_modules)
        executed_at = _utc_now_iso()
        sent: list[str] = []
        failed: list[str] = []
        error_messages: list[str] = []

        if not preview.get("ok"):
            failed = list(selected_channels)
            error_messages.append(str(preview.get("error") or "preview_unavailable"))
        else:
            if "email" in selected_channels:
                email_result = self._send_email(config, subject=preview["subject"], text_body=preview["text_body"], html_body=preview["html_body"])
                if email_result is True:
                    sent.append("email")
                else:
                    failed.append("email")
                    error_messages.append(email_result)

        status = "success" if sent and not failed else "partial" if sent else "failed"
        detail = " / ".join(error_messages) if error_messages else "发送完成"
        run_record = {
            "executed_at": executed_at,
            "trigger": trigger,
            "job_name": job_name,
            "status": status,
            "detail": detail,
            "subject": preview.get("subject", ""),
            "channel_types": selected_channels,
            "module_ids": selected_modules,
        }
        recent_runs = self._append_recent_run(list(config.get("recent_runs") or []), run_record)
        return {
            "ok": bool(sent),
            "preview": preview,
            "recent_runs": recent_runs,
            "result": {
                "status": status,
                "executed_at": executed_at,
                "trigger": trigger,
                "job_name": job_name,
                "sent": sent,
                "failed": failed,
                "detail": detail,
            },
        }

    def _send_email(self, config: Mapping[str, Any], *, subject: str, text_body: str, html_body: str) -> bool | str:
        email = dict(config.get("email") or {})
        notifier = self._email_notifier_factory(
            smtp_server=email.get("smtp_server") or None,
            smtp_port=email.get("smtp_port") or None,
            smtp_use_tls=email.get("use_tls"),
            username=email.get("username") or None,
            password=email.get("password") or None,
            from_address=email.get("from_address") or None,
            email_to=email.get("to_addresses") or None,
        )
        if notifier.send(text_body, subject=subject, html_content=html_body):
            return True
        return getattr(notifier, "last_error", "") or "email_delivery_failed"

    def _module_status(self, config: Mapping[str, Any], preview: Mapping[str, Any]) -> str:
        email = config.get("email") or {}
        required = (
            email.get("smtp_server"),
            email.get("smtp_port"),
            email.get("to_addresses"),
        )
        if not all(required):
            return "degraded"
        if not preview.get("ok"):
            return "degraded"
        return "compatible"

    def _public_config(self, config: Mapping[str, Any]) -> dict[str, Any]:
        public = deepcopy(dict(config))
        email = public.setdefault("email", {})
        email["password_configured"] = bool(email.get("password"))
        return public

    def _ensure_config_file(self) -> None:
        if self._config_path.exists():
            return
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_config(DEFAULT_PUSH_CONFIG)

    def _load_config(self) -> dict[str, Any]:
        with self._config_lock:
            try:
                with self._config_path.open("r", encoding="utf-8") as handle:
                    raw = json.load(handle)
            except (FileNotFoundError, json.JSONDecodeError):
                raw = deepcopy(DEFAULT_PUSH_CONFIG)
            return self._normalize_config(raw, base=DEFAULT_PUSH_CONFIG)

    def _save_config(self, payload: Mapping[str, Any]) -> None:
        normalized = self._normalize_config(payload, base=DEFAULT_PUSH_CONFIG)
        with self._config_lock:
            self._write_config(normalized)

    def _unwrap_payload(self, payload: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
        if payload is None:
            return None
        nested = payload.get("config")
        if isinstance(nested, Mapping):
            unwrapped = dict(nested)
            if "persist" in payload:
                unwrapped["persist"] = payload.get("persist")
            return unwrapped
        return payload

    def _write_config(self, payload: Mapping[str, Any]) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._config_path.with_suffix(f"{self._config_path.suffix}.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        temp_path.replace(self._config_path)

    def _normalize_config(self, payload: Mapping[str, Any], *, base: Mapping[str, Any]) -> dict[str, Any]:
        merged = deepcopy(dict(base))
        if "selected_module_ids" in payload:
            merged["selected_module_ids"] = self._normalize_module_ids(payload.get("selected_module_ids"))
        else:
            merged["selected_module_ids"] = self._normalize_module_ids(merged.get("selected_module_ids"))

        merged["report_style"] = self._normalize_style(payload.get("report_style", merged.get("report_style")))
        merged["email"] = self._normalize_email_config(payload.get("email", merged.get("email")))
        merged["schedules"] = self._normalize_schedules(
            payload.get("schedules", merged.get("schedules")),
            default_module_ids=merged["selected_module_ids"],
        )
        merged["recent_runs"] = self._normalize_recent_runs(payload.get("recent_runs", merged.get("recent_runs")))
        merged["scheduler_history"] = dict(payload.get("scheduler_history", merged.get("scheduler_history", {})))
        self._trim_scheduler_history(merged)
        return merged

    def _normalize_module_ids(self, raw_value: Any) -> list[str]:
        allowed = {item["id"] for item in AVAILABLE_SOURCE_MODULES if item["enabled"]}
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        normalized = [str(value).strip() for value in values if str(value).strip() in allowed]
        return normalized or ["market"]

    def _normalize_style(self, value: Any) -> str:
        allowed = {item["id"] for item in STYLE_OPTIONS}
        text = str(value or "").strip().lower()
        return text if text in allowed else "newspaper"

    def _normalize_email_config(self, raw_value: Any) -> dict[str, Any]:
        base = deepcopy(DEFAULT_PUSH_CONFIG["email"])
        data = dict(raw_value or {})
        base["enabled"] = bool(data.get("enabled", base["enabled"]))
        base["label"] = str(data.get("label", base["label"]) or base["label"]).strip()
        base["smtp_server"] = str(data.get("smtp_server", base["smtp_server"]) or "").strip()
        base["smtp_port"] = self._normalize_port(data.get("smtp_port", base["smtp_port"]))
        base["use_tls"] = bool(data.get("use_tls", base["use_tls"]))
        base["username"] = str(data.get("username", "") or "").strip()
        base["password"] = str(data.get("password", "") or "")
        base["from_address"] = str(data.get("from_address", "") or "").strip()
        base["to_addresses"] = str(data.get("to_addresses", "") or "").strip()
        return base

    def _normalize_port(self, value: Any) -> int:
        try:
            port = int(value)
        except (TypeError, ValueError):
            return 587
        return port if 1 <= port <= 65535 else 587

    def _normalize_schedules(self, raw_value: Any, *, default_module_ids: list[str]) -> list[dict[str, Any]]:
        schedules = raw_value if isinstance(raw_value, list) else DEFAULT_PUSH_CONFIG["schedules"]
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(schedules):
            schedule = dict(item or {})
            timezone = self._normalize_timezone(schedule.get("timezone"))
            times = self._normalize_times(schedule.get("times"))
            normalized.append(
                {
                    "id": str(schedule.get("id") or f"schedule-{index + 1}").strip(),
                    "name": str(schedule.get("name") or f"推送任务 {index + 1}").strip(),
                    "enabled": bool(schedule.get("enabled", True)),
                    "module_ids": self._normalize_module_ids(schedule.get("module_ids") or default_module_ids),
                    "channel_types": self._normalize_channel_types(schedule.get("channel_types")),
                    "times": times or ["08:00"],
                    "timezone": timezone,
                }
            )
        return normalized or deepcopy(DEFAULT_PUSH_CONFIG["schedules"])

    def _normalize_channel_types(self, raw_value: Any) -> list[str]:
        allowed = {item["id"] for item in SUPPORTED_CHANNEL_TYPES if item["enabled"]}
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        normalized = [str(value).strip().lower() for value in values if str(value).strip().lower() in allowed]
        return normalized or ["email"]

    def _normalize_times(self, raw_value: Any) -> list[str]:
        values: list[str]
        if isinstance(raw_value, list):
            values = [str(item).strip() for item in raw_value]
        elif raw_value is None:
            values = []
        else:
            values = [part.strip() for part in str(raw_value).split(",")]
        normalized = [value for value in values if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value)]
        deduped: list[str] = []
        for item in normalized:
            if item not in deduped:
                deduped.append(item)
        return deduped

    def _normalize_timezone(self, value: Any) -> str:
        candidate = str(value or DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE
        try:
            ZoneInfo(candidate)
            return candidate
        except ZoneInfoNotFoundError:
            return DEFAULT_TIMEZONE

    def _normalize_recent_runs(self, raw_value: Any) -> list[dict[str, Any]]:
        runs = raw_value if isinstance(raw_value, list) else []
        normalized: list[dict[str, Any]] = []
        for item in runs[:12]:
            record = dict(item or {})
            normalized.append(
                {
                    "executed_at": str(record.get("executed_at") or _utc_now_iso()),
                    "trigger": str(record.get("trigger") or "manual"),
                    "job_name": str(record.get("job_name") or "推送任务"),
                    "status": str(record.get("status") or "unknown"),
                    "detail": str(record.get("detail") or ""),
                    "subject": str(record.get("subject") or ""),
                    "channel_types": list(record.get("channel_types") or []),
                    "module_ids": list(record.get("module_ids") or []),
                }
            )
        return normalized

    def _append_recent_run(self, recent_runs: list[dict[str, Any]], record: Mapping[str, Any]) -> list[dict[str, Any]]:
        items = [dict(record)] + [dict(item) for item in recent_runs]
        return self._normalize_recent_runs(items)

    def _is_schedule_due(self, schedule: Mapping[str, Any], now: datetime, config: Mapping[str, Any]) -> bool:
        timezone = ZoneInfo(str(schedule.get("timezone") or DEFAULT_TIMEZONE))
        local_now = now.astimezone(timezone)
        current_slot = local_now.strftime("%H:%M")
        if current_slot not in list(schedule.get("times") or []):
            return False
        history_key = self._schedule_history_key(schedule, now)
        return history_key not in dict(config.get("scheduler_history") or {})

    def _schedule_history_key(self, schedule: Mapping[str, Any], now: datetime) -> str:
        timezone = ZoneInfo(str(schedule.get("timezone") or DEFAULT_TIMEZONE))
        local_now = now.astimezone(timezone)
        return f"{schedule.get('id')}@{local_now.strftime('%Y-%m-%dT%H:%M')}"

    def _trim_scheduler_history(self, config: dict[str, Any]) -> None:
        history = dict(config.get("scheduler_history") or {})
        if len(history) <= 128:
            config["scheduler_history"] = history
            return
        sorted_items = sorted(history.items(), key=lambda item: item[1], reverse=True)
        config["scheduler_history"] = dict(sorted_items[:128])
