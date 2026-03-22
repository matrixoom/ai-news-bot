"""Live external-data providers with sample-data fallback wrappers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import inspect
import json
import os
import re
from typing import Any, Callable, Iterable, Sequence
from urllib.parse import quote_plus

import feedparser
from openai import OpenAI
import requests

from ..domain.external_data import (
    ConfidenceLevel,
    EventHorizon,
    MacroIndicatorReading,
    MarketIndexHistoryPoint,
    MarketIndexSnapshot,
    NewsCategory,
    NewsItem,
    ResearchFinding,
    SearchResultItem,
    SourceReference,
)
from ..logger import setup_logger
from .contracts import ProviderAvailability, ProviderStatus


logger = setup_logger(__name__)


class ProviderConfigurationError(RuntimeError):
    """Raised when a live provider lacks required local configuration."""


def _checked_at() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _clean_html(text: str | None) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _coerce_datetime(value: str | None) -> str | None:
    if not value:
        return None

    text = value.strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat().replace("+00:00", "Z")
    except ValueError:
        pass

    for format_text in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(text, format_text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        except ValueError:
            continue

    return text


def _coerce_date_text(value: Any) -> str:
    if value is None:
        return "暂无数据"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _pick_first(mapping: dict[str, Any], names: Iterable[str]) -> Any | None:
    for name in names:
        if name in mapping:
            return mapping[name]
    return None


@dataclass
class _ProviderRuntimeState:
    availability: ProviderAvailability
    detail: str


class _FallbackStatusMixin:
    """Keep the last availability and detail for dashboard diagnostics."""

    def __init__(self, provider_key: str, default_detail: str) -> None:
        self.provider_key = provider_key
        self._state = _ProviderRuntimeState(
            availability=ProviderAvailability.DEGRADED,
            detail=default_detail,
        )

    def _set_state(self, availability: ProviderAvailability, detail: str) -> None:
        self._state = _ProviderRuntimeState(availability=availability, detail=detail)

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=self._state.availability,
            detail=self._state.detail,
            checked_at=_checked_at(),
        )


class PublicRssNewsProvider:
    """Fetch technology, finance, and policy headlines from public RSS feeds."""

    provider_key = "public-rss-news"
    _USER_AGENT = "ai-news-bot/1.0 (+https://github.com/giftedunicorn/ai-news-bot)"
    _CATEGORY_FEEDS: dict[NewsCategory, tuple[tuple[str, str], ...]] = {
        NewsCategory.TECHNOLOGY: (
            ("OpenAI Blog", "https://openai.com/blog/rss/"),
            ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
            ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
        ),
        NewsCategory.FINANCE: (
            (
                "Google News Finance",
                "https://news.google.com/rss/search?q=finance+markets+when:1d&hl=en-US&gl=US&ceid=US:en",
            ),
            (
                "Google News A-Share",
                "https://news.google.com/rss/search?q=A-share+Hong+Kong+market+when:1d&hl=en-US&gl=US&ceid=US:en",
            ),
        ),
        NewsCategory.POLICY: (
            ("Gov.cn", "https://www.gov.cn/pushinfo/v150203/pushinfo.xml"),
            (
                "Google News Policy",
                "https://news.google.com/rss/search?q=China+policy+briefing+when:1d&hl=en-US&gl=US&ceid=US:en",
            ),
        ),
    }

    def fetch_latest(
        self,
        *,
        category: NewsCategory,
        published_on: date,
        limit: int,
    ) -> Sequence[NewsItem]:
        items: list[NewsItem] = []
        for source_name, feed_url in self._CATEGORY_FEEDS.get(category, ()):
            items.extend(
                self._fetch_feed_items(
                    category=category,
                    source_name=source_name,
                    feed_url=feed_url,
                    limit=limit,
                )
            )
            if len(items) >= limit:
                break
        return items[:limit]

    def _fetch_feed_items(
        self,
        *,
        category: NewsCategory,
        source_name: str,
        feed_url: str,
        limit: int,
    ) -> list[NewsItem]:
        response = requests.get(
            feed_url,
            headers={"User-Agent": self._USER_AGENT},
            timeout=8,
        )
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        if parsed.bozo and not parsed.entries:
            raise RuntimeError(f"Malformed RSS response from {feed_url}")

        items: list[NewsItem] = []
        for entry in parsed.entries[:limit]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if not title or not link:
                continue

            published_at = _coerce_datetime(
                getattr(entry, "published", None) or getattr(entry, "updated", None)
            ) or _checked_at()
            summary = _clean_html(
                getattr(entry, "summary", None) or getattr(entry, "description", None)
            )
            items.append(
                NewsItem(
                    provider=self.provider_key,
                    source_name=source_name,
                    category=category,
                    title=title,
                    url=link,
                    published_at=published_at,
                    summary=summary or None,
                )
            )
        return items

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail="公共 RSS 数据源已配置，可用于仪表盘新闻抓取。",
            checked_at=_checked_at(),
        )


class GoogleNewsSearchProvider:
    """Use Google News RSS search as a public hotspot-recall source."""

    provider_key = "google-news-search"
    _USER_AGENT = "ai-news-bot/1.0 (+https://github.com/giftedunicorn/ai-news-bot)"

    def search(
        self,
        *,
        query: str,
        published_on: date,
        limit: int,
    ) -> Sequence[SearchResultItem]:
        feed_url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(query + ' when:1d')}&hl=en-US&gl=US&ceid=US:en"
        )
        response = requests.get(
            feed_url,
            headers={"User-Agent": self._USER_AGENT},
            timeout=8,
        )
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        if parsed.bozo and not parsed.entries:
            raise RuntimeError(f"Malformed search RSS response for query: {query}")

        results: list[SearchResultItem] = []
        for entry in parsed.entries[:limit]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if not title or not link:
                continue

            published_at = _coerce_datetime(
                getattr(entry, "published", None) or getattr(entry, "updated", None)
            )
            snippet = _clean_html(
                getattr(entry, "summary", None) or getattr(entry, "description", None)
            )
            original_url = link
            if getattr(entry, "source", None) and getattr(entry.source, "href", None):
                original_url = entry.source.href

            results.append(
                SearchResultItem(
                    provider=self.provider_key,
                    query=query,
                    title=title,
                    snippet=snippet or title,
                    original_url=original_url,
                    published_at=published_at,
                )
            )
        return results

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail="Google News RSS 搜索已配置，可用于热点补充。",
            checked_at=_checked_at(),
        )


class AkshareMarketDataProvider:
    """Fetch tracked index closes and recent history through AKShare."""

    provider_key = "akshare-market"
    _SYMBOL_CONFIG: dict[str, tuple[tuple[str, dict[str, str]], ...]] = {
        "CSI300": (
            ("stock_zh_index_daily_em", {"symbol": "sh000300"}),
            ("stock_zh_index_daily", {"symbol": "sh000300"}),
        ),
        "CSI500": (
            ("stock_zh_index_daily_em", {"symbol": "sh000905"}),
            ("stock_zh_index_daily", {"symbol": "sh000905"}),
        ),
        "CSI1000": (
            ("stock_zh_index_daily_em", {"symbol": "sh000852"}),
            ("stock_zh_index_daily", {"symbol": "sh000852"}),
        ),
        "SSE": (
            ("stock_zh_index_daily_em", {"symbol": "sh000001"}),
            ("stock_zh_index_daily", {"symbol": "sh000001"}),
        ),
        "CHINEXT": (
            ("stock_zh_index_daily_em", {"symbol": "sz399006"}),
            ("stock_zh_index_daily", {"symbol": "sz399006"}),
        ),
        "HSTECH": (
            ("stock_hk_index_daily_sina", {"symbol": "HSTECH"}),
            ("stock_hk_index_daily_em", {"symbol": "HSTECF2L"}),
        ),
    }

    def fetch_index_snapshots(
        self,
        *,
        symbols: Sequence[str],
        trade_date: date,
    ) -> Sequence[MarketIndexSnapshot]:
        akshare = self._load_akshare()
        snapshots: list[MarketIndexSnapshot] = []
        for symbol in symbols:
            try:
                frame = self._load_market_frame(akshare=akshare, symbol=symbol, trade_date=trade_date)
            except Exception as exc:
                logger.warning("AKShare market fetch failed for %s: %s", symbol, exc)
                continue
            if frame is None:
                continue

            records = self._extract_market_records(frame)
            eligible = [record for record in records if record["trade_date"] <= trade_date]
            if not eligible:
                continue

            eligible.sort(key=lambda item: item["trade_date"])
            current_record = eligible[-1]
            lookback = tuple(item["close_price"] for item in eligible[-20:-1])
            history_points = tuple(
                MarketIndexHistoryPoint(
                    trade_date=item["trade_date"],
                    close_price=item["close_price"],
                )
                for item in eligible
            )
            snapshots.append(
                MarketIndexSnapshot(
                    provider=self.provider_key,
                    symbol=symbol,
                    display_name=symbol,
                    trade_date=current_record["trade_date"],
                    close_price=current_record["close_price"],
                    currency="HKD" if symbol == "HSTECH" else "CNY",
                    source_url="https://akshare.akfamily.xyz/data/index/index.html",
                    lookback_closes=lookback,
                    history_points=history_points,
                )
            )
        return snapshots

    def _load_akshare(self):
        try:
            import akshare as ak  # type: ignore
        except ImportError as exc:
            raise ProviderConfigurationError(
                "未安装 AKShare；请安装 'akshare' 包以启用实时市场数据。"
            ) from exc
        return ak

    def _load_market_frame(self, *, akshare, symbol: str, trade_date: date):
        candidates = self._SYMBOL_CONFIG.get(symbol, ())
        start_date = (trade_date - timedelta(days=180)).strftime("%Y%m%d")
        end_date = trade_date.strftime("%Y%m%d")

        last_error: Exception | None = None
        for function_name, kwargs in candidates:
            if not hasattr(akshare, function_name):
                continue

            call_kwargs = dict(kwargs)
            call_kwargs.setdefault("start_date", start_date)
            call_kwargs.setdefault("end_date", end_date)
            try:
                return self._call_akshare_function(
                    function=getattr(akshare, function_name),
                    call_kwargs=call_kwargs,
                )
            except Exception as exc:  # pragma: no cover - exercised through wrapper
                last_error = exc

        if last_error is not None:
            raise last_error
        return None

    def _call_akshare_function(self, *, function, call_kwargs: dict[str, Any]):
        try:
            signature = inspect.signature(function)
        except (TypeError, ValueError):
            return function(**call_kwargs)

        parameters = signature.parameters
        if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
            return function(**call_kwargs)

        filtered_kwargs = {
            key: value
            for key, value in call_kwargs.items()
            if key in parameters
        }
        return function(**filtered_kwargs)

    def _extract_market_records(self, frame) -> list[dict[str, Any]]:
        if frame is None or getattr(frame, "empty", True):
            return []

        records: list[dict[str, Any]] = []
        for row in frame.to_dict(orient="records"):
            trade_date_value = _pick_first(row, ("date", "日期", "时间", "trade_date"))
            close_value = _pick_first(row, ("close", "latest", "收盘", "收盘价", "Close", "Latest", "最新价"))
            if trade_date_value is None or close_value is None:
                continue

            try:
                records.append(
                    {
                        "trade_date": datetime.fromisoformat(str(trade_date_value)).date()
                        if "T" in str(trade_date_value)
                        else datetime.strptime(str(trade_date_value)[:10], "%Y-%m-%d").date(),
                        "close_price": float(close_value),
                    }
                )
            except ValueError:
                try:
                    records.append(
                        {
                            "trade_date": datetime.strptime(str(trade_date_value), "%Y%m%d").date(),
                            "close_price": float(close_value),
                        }
                    )
                except ValueError:
                    continue
        return records

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail="AKShare 市场端点已配置，可抓取宽基指数快照。",
            checked_at=_checked_at(),
        )


class AkshareMacroDataProvider:
    """Fetch a subset of macro indicators through AKShare."""

    provider_key = "akshare-macro"

    def fetch_latest_readings(
        self,
        *,
        indicator_codes: Sequence[str],
    ) -> Sequence[MacroIndicatorReading]:
        akshare = self._load_akshare()
        readings: list[MacroIndicatorReading] = []
        for code in indicator_codes:
            try:
                reading = self._fetch_one(akshare=akshare, indicator_code=code)
            except Exception as exc:
                logger.warning("AKShare macro fetch failed for %s: %s", code, exc)
                continue
            if reading is not None:
                readings.append(reading)
        return readings

    def _load_akshare(self):
        try:
            import akshare as ak  # type: ignore
        except ImportError as exc:
            raise ProviderConfigurationError(
                "未安装 AKShare；请安装 'akshare' 包以启用实时宏观数据。"
            ) from exc
        return ak

    def _fetch_one(self, *, akshare, indicator_code: str) -> MacroIndicatorReading | None:
        candidates: dict[str, tuple[str, str, tuple[str, ...]]] = {
            "cpi": ("macro_china_cpi_yearly", "%", ("同比", "value", "最新值")),
            "ppi": ("macro_china_ppi_yearly", "%", ("同比", "value", "最新值")),
            "social_financing": ("macro_china_shrzgm", "tn yuan", ("社会融资规模增量", "value", "最新值")),
            "gdp_real": ("macro_china_gdp_yearly", "%", ("同比增长", "value", "最新值")),
        }
        if indicator_code not in candidates:
            return None

        function_name, unit, preferred_columns = candidates[indicator_code]
        if not hasattr(akshare, function_name):
            return None

        frame = getattr(akshare, function_name)()
        if frame is None or getattr(frame, "empty", True):
            return None

        value_column = self._pick_numeric_column(frame=frame, preferred_columns=preferred_columns)
        period_column = self._pick_period_column(frame)
        if value_column is None or period_column is None:
            return None

        rows = frame.to_dict(orient="records")
        latest = rows[-1]
        previous = rows[-2] if len(rows) > 1 else None

        raw_value = float(latest[value_column])
        raw_previous = float(previous[value_column]) if previous and previous.get(value_column) is not None else None
        if unit == "tn yuan" and abs(raw_value) > 1000:
            raw_value = raw_value / 10000
            if raw_previous is not None:
                raw_previous = raw_previous / 10000

        change_value = raw_value - raw_previous if raw_previous is not None else None
        return MacroIndicatorReading(
            provider=self.provider_key,
            indicator_code=indicator_code,
            display_name=str(indicator_code).replace("_", " ").title(),
            value=raw_value,
            unit=unit,
            period_label=_coerce_date_text(latest.get(period_column)),
            released_at=date.today().isoformat(),
            source_url="https://akshare.akfamily.xyz/data/macro/macro.html",
            previous_value=raw_previous,
            change_value=change_value,
            change_kind="vs prior release" if change_value is not None else None,
            trend_summary=self._trend_summary(indicator_code, change_value),
        )

    def _pick_numeric_column(self, *, frame, preferred_columns: tuple[str, ...]) -> str | None:
        columns = list(frame.columns)
        for preferred in preferred_columns:
            for column in columns:
                if preferred in str(column):
                    return str(column)

        numeric = []
        for column in columns:
            series = frame[column]
            try:
                converted = series.astype(float)
            except Exception:
                continue
            if converted.notna().any():
                numeric.append(str(column))
        return numeric[-1] if numeric else None

    def _pick_period_column(self, frame) -> str | None:
        columns = [str(column) for column in frame.columns]
        for preferred in ("月份", "季度", "date", "日期", "时间", "period"):
            for column in columns:
                if preferred == column or preferred in column:
                    return column
        return columns[0] if columns else None

    def _trend_summary(self, indicator_code: str, change_value: float | None) -> str | None:
        if change_value is None:
            return None
        if change_value > 0:
            return f"{indicator_code} 较上次发布有所上升。"
        if change_value < 0:
            return f"{indicator_code} 较上次发布有所回落。"
        return f"{indicator_code} 与上次发布相比基本持平。"

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail="AKShare 宏观端点已配置，可用于实时指标采集。",
            checked_at=_checked_at(),
        )


class ArkResearchProvider:
    """Collect event-outlook findings through Volcengine Ark when configured."""

    provider_key = "ark-research"

    def __init__(self) -> None:
        api_key = os.getenv("ARK_API_KEY") or os.getenv("VOLCENGINE_ARK_API_KEY")
        model = os.getenv("ARK_MODEL") or os.getenv("VOLCENGINE_ARK_MODEL")
        base_url = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        if not api_key or not model:
            raise ProviderConfigurationError(
                "实时事件研究需要配置 ARK_API_KEY/VOLCENGINE_ARK_API_KEY 和 ARK_MODEL/VOLCENGINE_ARK_MODEL。"
            )
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def collect_outlook(
        self,
        *,
        horizon: EventHorizon,
        topics: Sequence[str],
        as_of: date,
    ) -> Sequence[ResearchFinding]:
        prompt = self._build_prompt(horizon=horizon, topics=topics, as_of=as_of)
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": "You are a policy and macro research assistant. Return strict JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or "[]"
        payload = json.loads(content)
        findings: list[ResearchFinding] = []
        for item in payload:
            sources = tuple(
                SourceReference(
                    title=str(source.get("title", "Source")),
                    url=str(source.get("url", "")),
                )
                for source in item.get("sources", [])
                if source.get("url")
            )
            findings.append(
                ResearchFinding(
                    provider=self.provider_key,
                    horizon=horizon,
                    title=str(item.get("title", "")).strip(),
                    region=str(item.get("region", "CN")),
                    expected_date=str(item.get("expected_date", "")),
                    summary=str(item.get("summary", "")).strip(),
                    confidence=ConfidenceLevel(str(item.get("confidence", "low")).lower()),
                    sources=sources,
                )
            )
        return [finding for finding in findings if finding.title and finding.summary]

    def _build_prompt(self, *, horizon: EventHorizon, topics: Sequence[str], as_of: date) -> str:
        return (
            "Return a JSON array. Each item must contain title, region, expected_date, summary, confidence, sources.\n"
            f"As of date: {as_of.isoformat()}\n"
            f"Horizon: {horizon.value}\n"
            f"Topics: {', '.join(topics)}\n"
            "Focus only on China, United States, Euro Area, and Japan.\n"
            "Prioritize official calendars, policy meeting schedules, and official statistical release calendars.\n"
            "Only include medium or high confidence events that can be backed by official or top-tier source links."
        )

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail="火山引擎 Ark 研究数据源已配置。",
            checked_at=_checked_at(),
        )


class UnavailableResearchProvider:
    """Return no event findings so missing event data remains visible."""

    provider_key = "unavailable-research"

    def collect_outlook(
        self,
        *,
        horizon: EventHorizon,
        topics: Sequence[str],
        as_of: date,
    ) -> Sequence[ResearchFinding]:
        _ = horizon, topics, as_of
        return []

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.UNAVAILABLE,
            detail="事件展望未接入样例回退数据，当前无可展示事件。",
            checked_at=_checked_at(),
        )


class FallbackNewsProvider(_FallbackStatusMixin):
    """Fallback wrapper for real-to-sample news ingestion."""

    def __init__(self, primary, fallback) -> None:
        super().__init__("news-live-fallback", "实时 RSS 新闻")
        self._primary = primary
        self._fallback = fallback
        self._primary_failed = False

    def fetch_latest(self, *, category: NewsCategory, published_on: date, limit: int) -> Sequence[NewsItem]:
        if self._primary_failed:
            return list(self._fallback.fetch_latest(category=category, published_on=published_on, limit=limit))
        try:
            items = list(self._primary.fetch_latest(category=category, published_on=published_on, limit=limit))
            self._set_state(ProviderAvailability.LIVE, f"实时新闻：{self._primary.provider_key}")
            return items
        except Exception as exc:
            self._primary_failed = True
            logger.warning("News provider fallback triggered: %s", exc)
            self._set_state(
                ProviderAvailability.DEGRADED,
                f"实时新闻不可用（{exc}）",
            )
            return list(self._fallback.fetch_latest(category=category, published_on=published_on, limit=limit))


class FallbackSearchProvider(_FallbackStatusMixin):
    """Fallback wrapper for real-to-sample search enrichment."""

    def __init__(self, primary, fallback) -> None:
        super().__init__("search-live-fallback", "实时搜索补充")
        self._primary = primary
        self._fallback = fallback
        self._primary_failed = False

    def search(self, *, query: str, published_on: date, limit: int) -> Sequence[SearchResultItem]:
        if self._primary_failed:
            return list(self._fallback.search(query=query, published_on=published_on, limit=limit))
        try:
            items = list(self._primary.search(query=query, published_on=published_on, limit=limit))
            self._set_state(ProviderAvailability.LIVE, f"实时搜索补充：{self._primary.provider_key}")
            return items
        except Exception as exc:
            self._primary_failed = True
            logger.warning("Search provider fallback triggered: %s", exc)
            self._set_state(
                ProviderAvailability.DEGRADED,
                f"实时搜索补充不可用（{exc}）",
            )
            return list(self._fallback.search(query=query, published_on=published_on, limit=limit))


class FallbackMacroProvider(_FallbackStatusMixin):
    """Fallback wrapper for live macro collection with partial sample backfill."""

    def __init__(self, primary, fallback) -> None:
        super().__init__("macro-live-fallback", "实时宏观读数")
        self._primary = primary
        self._fallback = fallback
        self._primary_failed = False

    def fetch_latest_readings(self, *, indicator_codes: Sequence[str]) -> Sequence[MacroIndicatorReading]:
        requested = list(indicator_codes)
        if self._primary_failed:
            return list(self._fallback.fetch_latest_readings(indicator_codes=requested))
        try:
            primary_items = list(self._primary.fetch_latest_readings(indicator_codes=requested))
        except Exception as exc:
            self._primary_failed = True
            logger.warning("Macro provider fallback triggered: %s", exc)
            self._set_state(
                ProviderAvailability.DEGRADED,
                f"实时宏观数据不可用（{exc}）",
            )
            return list(self._fallback.fetch_latest_readings(indicator_codes=requested))

        primary_by_code = {item.indicator_code: item for item in primary_items}
        missing_codes = [code for code in requested if code not in primary_by_code]
        if not missing_codes:
            self._set_state(ProviderAvailability.LIVE, f"实时宏观读数：{self._primary.provider_key}")
            return primary_items

        fallback_items = list(self._fallback.fetch_latest_readings(indicator_codes=missing_codes))
        self._set_state(
            ProviderAvailability.DEGRADED,
            "缺少指标：" + ", ".join(missing_codes),
        )
        return [*primary_items, *fallback_items]


class FallbackMarketDataProvider(_FallbackStatusMixin):
    """Fallback wrapper for live market snapshots with partial sample backfill."""

    def __init__(self, primary, fallback) -> None:
        super().__init__("market-live-fallback", "实时市场快照")
        self._primary = primary
        self._fallback = fallback
        self._primary_failed = False

    def fetch_index_snapshots(self, *, symbols: Sequence[str], trade_date: date) -> Sequence[MarketIndexSnapshot]:
        requested = list(symbols)
        if self._primary_failed:
            return list(self._fallback.fetch_index_snapshots(symbols=requested, trade_date=trade_date))
        try:
            primary_items = list(self._primary.fetch_index_snapshots(symbols=requested, trade_date=trade_date))
        except Exception as exc:
            self._primary_failed = True
            logger.warning("Market provider fallback triggered: %s", exc)
            self._set_state(
                ProviderAvailability.DEGRADED,
                f"实时市场数据不可用（{exc}）",
            )
            return list(self._fallback.fetch_index_snapshots(symbols=requested, trade_date=trade_date))

        primary_by_symbol = {item.symbol: item for item in primary_items}
        missing_symbols = [symbol for symbol in requested if symbol not in primary_by_symbol]
        if not missing_symbols:
            self._set_state(ProviderAvailability.LIVE, f"实时市场快照：{self._primary.provider_key}")
            return primary_items

        fallback_items = list(self._fallback.fetch_index_snapshots(symbols=missing_symbols, trade_date=trade_date))
        self._set_state(
            ProviderAvailability.DEGRADED,
            "缺少指数：" + ", ".join(missing_symbols),
        )
        return [*primary_items, *fallback_items]


class FallbackResearchProvider(_FallbackStatusMixin):
    """Fallback wrapper for live research with sample backfill."""

    def __init__(self, primary_factory: Callable[[], Any], fallback) -> None:
        super().__init__("research-live-fallback", "实时事件研究")
        self._primary_factory = primary_factory
        self._fallback = fallback
        self._primary = None
        self._primary_failed = False

    def collect_outlook(
        self,
        *,
        horizon: EventHorizon,
        topics: Sequence[str],
        as_of: date,
    ) -> Sequence[ResearchFinding]:
        if self._primary_failed:
            return list(self._fallback.collect_outlook(horizon=horizon, topics=topics, as_of=as_of))
        try:
            if self._primary is None:
                self._primary = self._primary_factory()
            items = list(self._primary.collect_outlook(horizon=horizon, topics=topics, as_of=as_of))
            self._set_state(ProviderAvailability.LIVE, f"实时事件研究：{self._primary.provider_key}")
            return items
        except ProviderConfigurationError as exc:
            self._primary_failed = True
            logger.warning("Research provider fallback triggered: %s", exc)
            self._set_state(
                ProviderAvailability.DEGRADED,
                f"实时事件研究不可用（{exc}）",
            )
            return list(self._fallback.collect_outlook(horizon=horizon, topics=topics, as_of=as_of))
        except Exception as exc:
            self._primary_failed = True
            logger.warning("Research provider fallback triggered: %s", exc)
            self._set_state(
                ProviderAvailability.DEGRADED,
                f"实时事件研究不可用（{exc}）",
            )
            return list(self._fallback.collect_outlook(horizon=horizon, topics=topics, as_of=as_of))
