"""NewsNow-backed provider implementations for broader realtime news ingestion."""
from __future__ import annotations

import atexit
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from typing import Callable, Iterable, Sequence
from urllib.parse import quote_plus, urlparse
from zoneinfo import ZoneInfo

import requests

from ..domain.external_data import NewsCategory, NewsItem
from ..logger import setup_logger
from .contracts import ProviderAvailability, ProviderStatus
from .newsnow_sources import NEWSNOW_ACTIVE_SOURCE_SPECS, NewsNowSource


logger = setup_logger(__name__)


def _checked_at() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _iso_from_epoch(epoch_ms: int) -> str:
    return datetime.fromtimestamp(epoch_ms / 1000, UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _coerce_datetime(value: object) -> str | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        epoch = int(value)
        if epoch > 10_000_000_000:
            return _iso_from_epoch(epoch)
        return _iso_from_epoch(epoch * 1000)

    text = str(value).strip()
    if not text:
        return None

    if text.isdigit():
        epoch = int(text)
        if epoch > 10_000_000_000:
            return _iso_from_epoch(epoch)
        return _iso_from_epoch(epoch * 1000)

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(text, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    except ValueError:
        return None


def _parse_iso_for_sort(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=UTC)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)


def _normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _extract_html_attr(tag_attrs: str, attr_name: str) -> str:
    pattern = re.compile(rf"""\b{re.escape(attr_name)}\s*=\s*(['"])(.*?)\1""", re.I | re.S)
    match = pattern.search(tag_attrs)
    if not match:
        return ""
    return _normalize_text(match.group(2))


def _extract_anchors_by_class(html: str, class_keyword: str) -> list[tuple[str, str]]:
    anchors: list[tuple[str, str]] = []
    for match in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, flags=re.I | re.S):
        attrs = match.group(1)
        body = match.group(2)
        class_name = _extract_html_attr(attrs, "class")
        if class_keyword not in class_name:
            continue
        href = _extract_html_attr(attrs, "href")
        if not href:
            continue
        anchors.append((href, body))
    return anchors


@dataclass(frozen=True)
class _SourceCacheEntry:
    updated_ms: int
    items: tuple[NewsItem, ...]


class NewsNowSourceMode(StrEnum):
    HYBRID = "hybrid"
    API = "api"
    UPSTREAM = "upstream"


class _NewsNowUpstreamServerManager:
    """Start the local upstream NewsNow dev server on demand for native mode."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None
        atexit.register(self.stop)

    def ensure_running(self, *, base_url: str) -> None:
        parsed = urlparse(base_url)
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or hostname not in {"127.0.0.1", "localhost"}:
            return
        if os.getenv("NEWSNOW_UPSTREAM_AUTO_START", "1") == "0":
            return
        if self._is_healthy(base_url):
            return

        with self._lock:
            if self._is_healthy(base_url):
                return
            if self._process is None or self._process.poll() is not None:
                self._process = self._start_process(base_url=base_url)

        deadline = time.time() + float(os.getenv("NEWSNOW_UPSTREAM_START_TIMEOUT_SECONDS", "45"))
        while time.time() < deadline:
            if self._is_healthy(base_url):
                return
            time.sleep(1.0)
        raise RuntimeError(f"local upstream NewsNow server did not become healthy: {base_url}")

    def stop(self) -> None:
        with self._lock:
            if self._process is None:
                return
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
            self._process = None

    def _start_process(self, *, base_url: str) -> subprocess.Popen[str]:
        repo_dir = Path(os.getenv("NEWSNOW_UPSTREAM_PROJECT_DIR", ".local-temp-newsnow")).resolve()
        if not repo_dir.exists():
            raise RuntimeError(f"upstream NewsNow project directory not found: {repo_dir}")
        if not (repo_dir / "node_modules").exists():
            raise RuntimeError(f"upstream NewsNow dependencies are not installed: {repo_dir / 'node_modules'}")

        parsed = urlparse(base_url)
        host = parsed.hostname or "127.0.0.1"
        port = str(parsed.port or 5173)
        if os.name == "nt":
            command = ["cmd", "/c", "npm", "run", "dev", "--", "--host", host, "--port", port]
        else:
            command = ["npm", "run", "dev", "--", "--host", host, "--port", port]

        logger.info("Starting local upstream NewsNow dev server at %s from %s", base_url, repo_dir)
        return subprocess.Popen(
            command,
            cwd=str(repo_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _is_healthy(self, base_url: str) -> bool:
        try:
            response = requests.get(f"{base_url.rstrip('/')}/healthz", timeout=2.5)
            return response.ok
        except Exception:
            return False

    def describe(self, *, base_url: str) -> dict[str, object]:
        parsed = urlparse(base_url)
        hostname = (parsed.hostname or "").lower()
        is_local = parsed.scheme in {"http", "https"} and hostname in {"127.0.0.1", "localhost"}
        healthy = self._is_healthy(base_url)
        managed = self._process is not None and self._process.poll() is None
        if healthy:
            status = "running"
            detail = "upstream service is reachable"
        elif managed:
            status = "starting"
            detail = "upstream process started but health endpoint is not ready"
        elif is_local:
            status = "stopped"
            detail = "local upstream service is not running"
        else:
            status = "remote"
            detail = "upstream target is a remote service"
        return {
            "status": status,
            "healthy": healthy,
            "managed": managed,
            "is_local": is_local,
            "base_url": base_url,
            "detail": detail,
        }


_UPSTREAM_SERVER_MANAGER = _NewsNowUpstreamServerManager()


def get_upstream_service_status(base_url: str | None = None) -> dict[str, object]:
    resolved_base_url = base_url or os.getenv("NEWSNOW_UPSTREAM_BASE_URL", "http://127.0.0.1:5173")
    return _UPSTREAM_SERVER_MANAGER.describe(base_url=resolved_base_url)


class NewsNowAggregatedNewsProvider:
    """Fetch NewsNow source feeds and normalize them into project NewsItem records."""

    provider_key = "newsnow-aggregated-news"
    _DEFAULT_BASE_URL = "https://newsnow.busiyi.world"
    _USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        *,
        base_url: str | None = None,
        source_specs: Sequence[NewsNowSource] = NEWSNOW_ACTIVE_SOURCE_SPECS,
        request_timeout_seconds: float | None = None,
        max_workers: int | None = None,
        max_items_per_source: int | None = None,
        min_source_budget: int | None = None,
        source_budget_multiplier: int | None = None,
        now_factory: Callable[[], datetime] | None = None,
        provider_key: str | None = None,
        auto_start_local_server: bool = False,
    ) -> None:
        self._base_url = (
            base_url
            or os.getenv("NEWSNOW_BASE_URL")
            or self._DEFAULT_BASE_URL
        ).rstrip("/")
        self._request_timeout_seconds = (
            request_timeout_seconds
            if request_timeout_seconds is not None
            else float(os.getenv("NEWSNOW_TIMEOUT_SECONDS", "8.0"))
        )
        self._max_workers = max(
            1,
            max_workers if max_workers is not None else int(os.getenv("NEWSNOW_MAX_WORKERS", "8")),
        )
        self._max_items_per_source = max(
            1,
            max_items_per_source
            if max_items_per_source is not None
            else int(os.getenv("NEWSNOW_MAX_ITEMS_PER_SOURCE", "3")),
        )
        self._min_source_budget = max(
            1,
            min_source_budget
            if min_source_budget is not None
            else int(os.getenv("NEWSNOW_MIN_SOURCE_BUDGET", "8")),
        )
        self._source_budget_multiplier = max(
            1,
            source_budget_multiplier
            if source_budget_multiplier is not None
            else int(os.getenv("NEWSNOW_SOURCE_BUDGET_MULTIPLIER", "2")),
        )
        self._now_factory = now_factory or (lambda: datetime.now(UTC))
        self.provider_key = provider_key or self.provider_key
        self._auto_start_local_server = auto_start_local_server

        self._sources_by_id = {source.source_id: source for source in source_specs}
        self._sources_by_category = {
            NewsCategory.TECHNOLOGY: tuple(
                source for source in source_specs if source.column == "tech"
            ),
            NewsCategory.FINANCE: tuple(
                source for source in source_specs if source.column == "finance"
            ),
            NewsCategory.POLICY: tuple(
                source for source in source_specs if source.column in {"china", "world"}
            ),
        }
        self._cache_by_source: dict[str, _SourceCacheEntry] = {}
        self._cursor_by_category = {category: 0 for category in self._sources_by_category}

    def fetch_latest(
        self,
        *,
        category: NewsCategory,
        published_on: date,  # noqa: ARG002 - kept for contract consistency
        limit: int,
    ) -> Sequence[NewsItem]:
        sources = self._sources_by_category.get(category, ())
        if not sources:
            return []

        selected = self._select_sources_for_pull(category=category, limit=limit)
        pulled = self._pull_selected_sources(selected)

        combined: list[NewsItem] = []
        combined.extend(item for entry in pulled.values() for item in entry.items)

        for source in sources:
            if source.source_id in pulled:
                continue
            cached = self._cache_by_source.get(source.source_id)
            if cached:
                combined.extend(cached.items)

        if not combined:
            raise RuntimeError("newsnow returned no usable items and no cache fallback is available")

        deduped: dict[str, NewsItem] = {}
        for item in combined:
            key = self._dedupe_key(item.title, item.url)
            existing = deduped.get(key)
            if existing is None or _parse_iso_for_sort(item.published_at) > _parse_iso_for_sort(existing.published_at):
                deduped[key] = item

        ordered = sorted(
            deduped.values(),
            key=lambda item: (
                _parse_iso_for_sort(item.published_at),
                item.source_name.lower(),
                item.title.lower(),
            ),
            reverse=True,
        )
        return ordered[:limit]

    def list_source_ids(self) -> tuple[str, ...]:
        """Return all active NewsNow source IDs currently registered."""
        return tuple(self._sources_by_id.keys())

    def fetch_source_latest(self, *, source_id: str, limit: int = 10) -> Sequence[NewsItem]:
        """Fetch one specific NewsNow source by ID.

        This method allows source-by-source verification and live probing.
        """
        source = self._sources_by_id.get(source_id)
        if source is None:
            raise ValueError(f"unknown newsnow source id: {source_id}")

        entry = self._fetch_or_reuse_source(source)
        if not entry.items:
            # Single-source probes should try once more instead of returning a
            # transient empty payload cached in the first attempt.
            self._cache_by_source.pop(source_id, None)
            entry = self._fetch_or_reuse_source(source)
        items = sorted(
            entry.items,
            key=lambda item: (_parse_iso_for_sort(item.published_at), item.title.lower()),
            reverse=True,
        )
        return list(items[: max(1, limit)])

    def _select_sources_for_pull(self, *, category: NewsCategory, limit: int) -> tuple[NewsNowSource, ...]:
        sources = self._sources_by_category.get(category, ())
        if not sources:
            return ()

        budget = min(
            len(sources),
            max(self._min_source_budget, limit * self._source_budget_multiplier),
        )
        start = self._cursor_by_category[category] % len(sources)
        selected = [sources[(start + offset) % len(sources)] for offset in range(budget)]
        self._cursor_by_category[category] = (start + budget) % len(sources)
        return tuple(selected)

    def _pull_selected_sources(self, sources: Sequence[NewsNowSource]) -> dict[str, _SourceCacheEntry]:
        if not sources:
            return {}

        pulled: dict[str, _SourceCacheEntry] = {}
        worker_count = min(len(sources), self._max_workers)
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_by_source = {
                executor.submit(self._fetch_or_reuse_source, source): source
                for source in sources
            }
            for future in as_completed(future_by_source):
                source = future_by_source[future]
                try:
                    entry = future.result()
                    pulled[source.source_id] = entry
                except Exception as exc:  # pragma: no cover - network errors are environment-specific
                    logger.warning("NewsNow source fetch failed (%s): %s", source.source_id, exc)
        return pulled

    def _fetch_or_reuse_source(self, source: NewsNowSource) -> _SourceCacheEntry:
        now_ms = int(self._now_factory().timestamp() * 1000)
        cached = self._cache_by_source.get(source.source_id)
        if cached and (now_ms - cached.updated_ms) < source.interval_ms:
            return cached

        try:
            refreshed = self._fetch_source(source=source, now_ms=now_ms)
            if refreshed.items:
                self._cache_by_source[source.source_id] = refreshed
                return refreshed
            native_items = self._fetch_native_source_items(source=source, now_ms=now_ms)
            if native_items:
                native_entry = _SourceCacheEntry(updated_ms=now_ms, items=tuple(native_items))
                self._cache_by_source[source.source_id] = native_entry
                return native_entry
            if cached:
                return cached
            self._cache_by_source[source.source_id] = refreshed
            return refreshed
        except Exception:
            native_items = self._fetch_native_source_items(source=source, now_ms=now_ms)
            if native_items:
                native_entry = _SourceCacheEntry(updated_ms=now_ms, items=tuple(native_items))
                self._cache_by_source[source.source_id] = native_entry
                return native_entry
            if cached:
                return cached
            raise

    def _fetch_source(self, *, source: NewsNowSource, now_ms: int) -> _SourceCacheEntry:
        if self._auto_start_local_server:
            _UPSTREAM_SERVER_MANAGER.ensure_running(base_url=self._base_url)
        payload = None
        last_error: Exception | None = None
        for _ in range(2):
            try:
                response = requests.get(
                    f"{self._base_url}/api/s",
                    params={"id": source.source_id, "latest": "true"},
                    headers={"User-Agent": self._USER_AGENT},
                    timeout=self._request_timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
                break
            except Exception as exc:
                last_error = exc
                payload = None
        if payload is None:
            if last_error is not None:
                raise last_error
            return _SourceCacheEntry(updated_ms=now_ms, items=())

        if not isinstance(payload, dict):
            return _SourceCacheEntry(updated_ms=now_ms, items=())

        updated_ms = payload.get("updatedTime")
        try:
            updated_ms = int(updated_ms)
        except (TypeError, ValueError):
            updated_ms = now_ms

        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            return _SourceCacheEntry(updated_ms=updated_ms, items=())

        category = self._category_from_column(source.column)
        if category is None:
            return _SourceCacheEntry(updated_ms=updated_ms, items=())

        normalized: list[NewsItem] = []
        fetched_at_text = _iso_from_epoch(updated_ms)
        for raw in raw_items[: self._max_items_per_source]:
            if not isinstance(raw, dict):
                continue
            title = _normalize_text(raw.get("title"))
            url = _normalize_text(raw.get("mobileUrl")) or _normalize_text(raw.get("url"))
            if not title or not url:
                continue

            extra = raw.get("extra") if isinstance(raw.get("extra"), dict) else {}
            published_at = (
                _coerce_datetime(raw.get("pubDate"))
                or _coerce_datetime(extra.get("date") if isinstance(extra, dict) else None)
                or fetched_at_text
            )
            summary = _normalize_text(extra.get("hover") if isinstance(extra, dict) else "")
            normalized.append(
                self._build_news_item(
                    source=source,
                    title=title,
                    url=url,
                    published_at=published_at,
                    summary=summary or None,
                )
            )
        return _SourceCacheEntry(updated_ms=updated_ms, items=tuple(normalized))

    def _build_news_item(
        self,
        *,
        source: NewsNowSource,
        title: str,
        url: str,
        published_at: str,
        summary: str | None,
    ) -> NewsItem:
        category = self._category_from_column(source.column)
        if category is None:
            raise RuntimeError(f"unsupported source column: {source.column}")
        return NewsItem(
            provider=self.provider_key,
            source_name=source.source_id,
            category=category,
            title=title,
            url=url,
            published_at=published_at,
            summary=summary,
        )

    def _fetch_native_source_items(self, *, source: NewsNowSource, now_ms: int) -> list[NewsItem]:
        source_id = source.source_id
        try:
            if source_id == "bilibili-hot-search":
                return self._native_bilibili_hot_search(source=source, now_ms=now_ms)
            if source_id == "bilibili-hot-video":
                return self._native_bilibili_video_list(
                    source=source,
                    endpoint="https://api.bilibili.com/x/web-interface/popular",
                    now_ms=now_ms,
                )
            if source_id == "bilibili-ranking":
                return self._native_bilibili_video_list(
                    source=source,
                    endpoint="https://api.bilibili.com/x/web-interface/ranking/v2",
                    now_ms=now_ms,
                )
            if source_id == "kuaishou":
                return self._native_kuaishou_hot_search(source=source, now_ms=now_ms)
            if source_id == "36kr-renqi":
                return self._native_36kr_renqi(source=source, now_ms=now_ms)
            if source_id in {"36kr", "36kr-quick"}:
                return self._native_36kr_quick(source=source, now_ms=now_ms)
            if source_id == "juejin":
                return self._native_juejin_hot(source=source, now_ms=now_ms)
            if source_id in {"fastbull", "fastbull-express"}:
                return self._native_fastbull_express(source=source, now_ms=now_ms)
            if source_id == "fastbull-news":
                return self._native_fastbull_news(source=source, now_ms=now_ms)
        except Exception as exc:  # pragma: no cover - network/output is non-deterministic
            logger.warning("Native source fallback failed (%s): %s", source_id, exc)
        return []

    def _native_bilibili_hot_search(self, *, source: NewsNowSource, now_ms: int) -> list[NewsItem]:
        response = requests.get(
            "https://s.search.bilibili.com/main/hotword",
            params={"limit": 30},
            headers={"User-Agent": self._USER_AGENT},
            timeout=max(6.0, self._request_timeout_seconds),
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("list") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return []

        published_at = _iso_from_epoch(now_ms)
        items: list[NewsItem] = []
        for row in rows[: self._max_items_per_source]:
            if not isinstance(row, dict):
                continue
            keyword = _normalize_text(row.get("keyword"))
            title = _normalize_text(row.get("show_name"))
            if not keyword or not title:
                continue
            url = f"https://search.bilibili.com/all?keyword={quote_plus(keyword)}"
            items.append(
                self._build_news_item(
                    source=source,
                    title=title,
                    url=url,
                    published_at=published_at,
                    summary=None,
                )
            )
        return items

    def _native_bilibili_video_list(
        self,
        *,
        source: NewsNowSource,
        endpoint: str,
        now_ms: int,
    ) -> list[NewsItem]:
        response = requests.get(
            endpoint,
            headers={"User-Agent": self._USER_AGENT},
            timeout=max(6.0, self._request_timeout_seconds),
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        rows = data.get("list") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return []

        items: list[NewsItem] = []
        for row in rows[: self._max_items_per_source]:
            if not isinstance(row, dict):
                continue
            bvid = _normalize_text(row.get("bvid"))
            title = _normalize_text(row.get("title"))
            if not bvid or not title:
                continue
            pub_date = _coerce_datetime(row.get("pubdate")) or _iso_from_epoch(now_ms)
            summary = _normalize_text(row.get("desc"))
            items.append(
                self._build_news_item(
                    source=source,
                    title=title,
                    url=f"https://www.bilibili.com/video/{bvid}",
                    published_at=pub_date,
                    summary=summary or None,
                )
            )
        return items

    def _native_kuaishou_hot_search(self, *, source: NewsNowSource, now_ms: int) -> list[NewsItem]:
        response = requests.get(
            "https://www.kuaishou.com/?isHome=1",
            headers={"User-Agent": self._USER_AGENT},
            timeout=max(6.0, self._request_timeout_seconds),
        )
        response.raise_for_status()
        html = response.text
        match = re.search(r"window\.__APOLLO_STATE__\s*=\s*(\{.*?\})\s*;", html, flags=re.S)
        if not match:
            return []

        payload = json.loads(match.group(1))
        default_client = payload.get("defaultClient") if isinstance(payload, dict) else None
        root_query = default_client.get("ROOT_QUERY") if isinstance(default_client, dict) else None
        rank_ref = root_query.get('visionHotRank({"page":"home"})') if isinstance(root_query, dict) else None
        hot_rank_id = rank_ref.get("id") if isinstance(rank_ref, dict) else None
        hot_rank_data = default_client.get(hot_rank_id) if isinstance(default_client, dict) and hot_rank_id else None
        rows = hot_rank_data.get("items") if isinstance(hot_rank_data, dict) else None
        if not isinstance(rows, list):
            return []

        published_at = _iso_from_epoch(now_ms)
        items: list[NewsItem] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item_id = _normalize_text(row.get("id"))
            if not item_id:
                continue
            hot_item = default_client.get(item_id) if isinstance(default_client, dict) else None
            if not isinstance(hot_item, dict):
                continue
            if _normalize_text(hot_item.get("tagType")) == "缃《":
                continue

            title = _normalize_text(hot_item.get("name"))
            if not title:
                continue
            url = f"https://www.kuaishou.com/search/video?searchKey={quote_plus(title)}"
            items.append(
                self._build_news_item(
                    source=source,
                    title=title,
                    url=url,
                    published_at=published_at,
                    summary=None,
                )
            )
            if len(items) >= self._max_items_per_source:
                break
        return items

    def _native_36kr_renqi(self, *, source: NewsNowSource, now_ms: int) -> list[NewsItem]:
        shanghai_day = self._now_factory().astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
        response = requests.get(
            f"https://36kr.com/hot-list/renqi/{shanghai_day}/1",
            headers={
                "User-Agent": self._USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://36kr.com/",
            },
            timeout=max(8.0, self._request_timeout_seconds),
        )
        response.raise_for_status()
        html = response.text
        rows = _extract_anchors_by_class(html, "article-item-title")
        if not rows:
            return self._native_36kr_quick(source=source, now_ms=now_ms)

        published_at = _iso_from_epoch(now_ms)
        items: list[NewsItem] = []
        for href, raw_title in rows:
            title = _normalize_text(_strip_tags(raw_title))
            if not title:
                continue
            url = href if href.startswith("http") else f"https://36kr.com{href}"
            items.append(
                self._build_news_item(
                    source=source,
                    title=title,
                    url=url,
                    published_at=published_at,
                    summary=None,
                )
            )
            if len(items) >= self._max_items_per_source:
                break
        return items

    def _native_36kr_quick(self, *, source: NewsNowSource, now_ms: int) -> list[NewsItem]:
        response = requests.get(
            "https://www.36kr.com/newsflashes",
            headers={"User-Agent": self._USER_AGENT, "Referer": "https://www.36kr.com/"},
            timeout=max(8.0, self._request_timeout_seconds),
        )
        response.raise_for_status()
        html = response.text
        rows = _extract_anchors_by_class(html, "item-title")
        if not rows:
            return []

        published_at = _iso_from_epoch(now_ms)
        items: list[NewsItem] = []
        for href, raw_title in rows:
            title = _normalize_text(_strip_tags(raw_title))
            if not title:
                continue
            url = href if href.startswith("http") else f"https://www.36kr.com{href}"
            items.append(
                self._build_news_item(
                    source=source,
                    title=title,
                    url=url,
                    published_at=published_at,
                    summary=None,
                )
            )
            if len(items) >= self._max_items_per_source:
                break
        return items

    def _native_juejin_hot(self, *, source: NewsNowSource, now_ms: int) -> list[NewsItem]:
        response = requests.get(
            "https://api.juejin.cn/content_api/v1/content/article_rank",
            params={"category_id": 1, "type": "hot", "spider": 0},
            headers={"User-Agent": self._USER_AGENT},
            timeout=max(8.0, self._request_timeout_seconds),
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return []

        published_at = _iso_from_epoch(now_ms)
        items: list[NewsItem] = []
        for row in rows[: self._max_items_per_source]:
            if not isinstance(row, dict):
                continue
            content = row.get("content") if isinstance(row.get("content"), dict) else {}
            content_id = _normalize_text(content.get("content_id"))
            title = _normalize_text(content.get("title"))
            if not content_id or not title:
                continue
            items.append(
                self._build_news_item(
                    source=source,
                    title=title,
                    url=f"https://juejin.cn/post/{content_id}",
                    published_at=published_at,
                    summary=None,
                )
            )
        return items

    def _native_fastbull_express(self, *, source: NewsNowSource, now_ms: int) -> list[NewsItem]:
        base_url = "https://www.fastbull.com"
        response = requests.get(
            f"{base_url}/cn/express-news",
            headers={"User-Agent": self._USER_AGENT},
            timeout=max(10.0, self._request_timeout_seconds),
        )
        response.raise_for_status()
        html = response.text

        rows: list[tuple[str, str, str]] = []
        for match in re.finditer(r'data-title="([^"]+)"\s+data-href="([^"]+)"', html, flags=re.I):
            title = _normalize_text(_strip_tags(match.group(1)))
            href = _normalize_text(match.group(2))
            if not title or not href:
                continue
            context = html[max(0, match.start() - 1200): match.start()]
            date_match = re.search(r'data-date="(\d{10,13})"', context)
            pub_date = _coerce_datetime(date_match.group(1)) if date_match else _iso_from_epoch(now_ms)
            rows.append((title, href, pub_date))

        items: list[NewsItem] = []
        for title, href, pub_date in rows:
            url = href if href.startswith("http") else f"{base_url}{href}"
            items.append(
                self._build_news_item(
                    source=source,
                    title=title,
                    url=url,
                    published_at=pub_date,
                    summary=None,
                )
            )
            if len(items) >= self._max_items_per_source:
                break
        return items

    def _native_fastbull_news(self, *, source: NewsNowSource, now_ms: int) -> list[NewsItem]:
        base_url = "https://www.fastbull.com"
        response = requests.get(
            f"{base_url}/cn/news",
            headers={"User-Agent": self._USER_AGENT},
            timeout=max(10.0, self._request_timeout_seconds),
        )
        response.raise_for_status()
        html = response.text

        anchors = _extract_anchors_by_class(html, "trending_type")
        items: list[NewsItem] = []
        for href, body in anchors:
            title_match = re.search(r"""<h\d[^>]*class="[^"]*\btitle\b[^"]*"[^>]*>(.*?)</h\d>""", body, re.I | re.S)
            title = _normalize_text(_strip_tags(title_match.group(1))) if title_match else ""
            if not title:
                continue
            date_match = re.search(r'data-date="(\d{10,13})"', body)
            pub_date = _coerce_datetime(date_match.group(1)) if date_match else _iso_from_epoch(now_ms)
            url = href if href.startswith("http") else f"{base_url}{href}"
            items.append(
                self._build_news_item(
                    source=source,
                    title=title,
                    url=url,
                    published_at=pub_date,
                    summary=None,
                )
            )
            if len(items) >= self._max_items_per_source:
                break
        return items

    def _category_from_column(self, column: str) -> NewsCategory | None:
        if column == "tech":
            return NewsCategory.TECHNOLOGY
        if column == "finance":
            return NewsCategory.FINANCE
        if column in {"china", "world"}:
            return NewsCategory.POLICY
        return None

    def _dedupe_key(self, title: str, url: str) -> str:
        normalized_title = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        if normalized_title:
            return normalized_title
        normalized_url = re.sub(r"[^a-z0-9]+", " ", url.lower()).strip()
        return normalized_url or "unknown"

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail=(
                f"NewsNow provider ready ({len(self._sources_by_id)} active sources, "
                f"base_url={self._base_url})."
            ),
            checked_at=_checked_at(),
        )


class NewsNowModeProvider:
    """Expose API, upstream, and hybrid NewsNow modes behind one provider contract."""

    provider_key = "newsnow-mode-provider"

    def __init__(
        self,
        *,
        mode: NewsNowSourceMode | str = NewsNowSourceMode.HYBRID,
        api_provider: NewsNowAggregatedNewsProvider | None = None,
        upstream_provider: NewsNowAggregatedNewsProvider | None = None,
    ) -> None:
        self._mode = NewsNowSourceMode(str(mode))
        self._api_provider = api_provider or NewsNowAggregatedNewsProvider(
            base_url=os.getenv("NEWSNOW_API_BASE_URL", NewsNowAggregatedNewsProvider._DEFAULT_BASE_URL),
            provider_key="newsnow-api-provider",
        )
        self._upstream_provider = upstream_provider or NewsNowAggregatedNewsProvider(
            base_url=os.getenv("NEWSNOW_UPSTREAM_BASE_URL", "http://127.0.0.1:5173"),
            provider_key="newsnow-upstream-provider",
            auto_start_local_server=True,
        )

    @property
    def mode(self) -> NewsNowSourceMode:
        return self._mode

    def fetch_latest(self, *, category: NewsCategory, published_on: date, limit: int) -> Sequence[NewsItem]:
        if self._mode == NewsNowSourceMode.API:
            return self._api_provider.fetch_latest(category=category, published_on=published_on, limit=limit)
        if self._mode == NewsNowSourceMode.UPSTREAM:
            return self._upstream_provider.fetch_latest(category=category, published_on=published_on, limit=limit)
        try:
            return self._api_provider.fetch_latest(category=category, published_on=published_on, limit=limit)
        except Exception:
            logger.warning("Falling back from NewsNow API mode to upstream native mode for %s", category.value)
            return self._upstream_provider.fetch_latest(category=category, published_on=published_on, limit=limit)

    def fetch_source_latest(self, *, source_id: str, limit: int = 10) -> Sequence[NewsItem]:
        if self._mode == NewsNowSourceMode.API:
            return self._api_provider.fetch_source_latest(source_id=source_id, limit=limit)
        if self._mode == NewsNowSourceMode.UPSTREAM:
            return self._upstream_provider.fetch_source_latest(source_id=source_id, limit=limit)
        try:
            return self._api_provider.fetch_source_latest(source_id=source_id, limit=limit)
        except Exception:
            logger.warning("Falling back from NewsNow API source probe to upstream native mode for %s", source_id)
            return self._upstream_provider.fetch_source_latest(source_id=source_id, limit=limit)

    def list_source_ids(self) -> tuple[str, ...]:
        return self._api_provider.list_source_ids()

    def healthcheck(self) -> ProviderStatus:
        if self._mode == NewsNowSourceMode.API:
            return self._api_provider.healthcheck()
        if self._mode == NewsNowSourceMode.UPSTREAM:
            return self._upstream_provider.healthcheck()
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail=(
                f"NewsNow hybrid mode active (api={self._api_provider._base_url}, "
                f"upstream={self._upstream_provider._base_url})."
            ),
            checked_at=_checked_at(),
        )


class CompositeNewsProvider:
    """Combine multiple news providers and merge their outputs."""

    provider_key = "composite-news"

    def __init__(self, providers: Iterable) -> None:
        self._providers = tuple(providers)

    def fetch_latest(self, *, category: NewsCategory, published_on: date, limit: int) -> Sequence[NewsItem]:
        merged: list[NewsItem] = []
        errors: list[Exception] = []

        for provider in self._providers:
            try:
                merged.extend(
                    provider.fetch_latest(
                        category=category,
                        published_on=published_on,
                        limit=limit,
                    )
                )
            except Exception as exc:
                errors.append(exc)
                logger.warning("Composite provider sub-provider failed (%s): %s", provider.provider_key, exc)

        deduped: dict[str, NewsItem] = {}
        for item in merged:
            key = self._dedupe_key(item.title, item.url)
            existing = deduped.get(key)
            if existing is None or _parse_iso_for_sort(item.published_at) > _parse_iso_for_sort(existing.published_at):
                deduped[key] = item

        if not deduped and errors and len(errors) == len(self._providers):
            raise RuntimeError("all composed news providers failed") from errors[-1]

        ordered = sorted(
            deduped.values(),
            key=lambda item: (_parse_iso_for_sort(item.published_at), item.source_name.lower()),
            reverse=True,
        )
        return ordered[:limit]

    def _dedupe_key(self, title: str, url: str) -> str:
        normalized_title = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        if normalized_title:
            return normalized_title
        normalized_url = re.sub(r"[^a-z0-9]+", " ", url.lower()).strip()
        return normalized_url or "unknown"

    def healthcheck(self) -> ProviderStatus:
        if not self._providers:
            return ProviderStatus(
                provider_key=self.provider_key,
                availability=ProviderAvailability.UNAVAILABLE,
                detail="No upstream provider configured.",
                checked_at=_checked_at(),
            )
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail=f"Composite provider active ({len(self._providers)} upstream providers).",
            checked_at=_checked_at(),
        )

