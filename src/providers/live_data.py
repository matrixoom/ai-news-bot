"""Live external-data providers with sample-data fallback wrappers."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from html import unescape
import io
import inspect
import json
import os
import re
from typing import Any, Callable, Iterable, Sequence
from urllib.parse import quote_plus, urljoin
from zoneinfo import ZoneInfo

import feedparser
from openai import OpenAI
import requests

from ..domain.external_data import (
    ConfidenceLevel,
    EventHorizon,
    MacroHistoryPoint,
    MacroIndicatorReading,
    MacroIndicatorSeries,
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


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def _quarter_end(year: int, quarter: int) -> date:
    return _month_end(year, quarter * 3)


def _iter_month_starts(start_date: date, end_date: date) -> Iterable[tuple[int, int]]:
    year = start_date.year
    month = start_date.month
    while (year, month) <= (end_date.year, end_date.month):
        yield year, month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1


def _parse_nbs_period_code(code: str) -> tuple[str, date]:
    text = str(code or "").strip()
    if len(text) == 6 and text.isdigit():
        year = int(text[:4])
        month = int(text[4:])
        return f"{year:04d}-{month:02d}", _month_end(year, month)
    if len(text) == 5 and text[:4].isdigit() and text[-1] in {"A", "B", "C", "D"}:
        year = int(text[:4])
        quarter = {"A": 1, "B": 2, "C": 3, "D": 4}[text[-1]]
        return f"{year:04d}-Q{quarter}", _quarter_end(year, quarter)
    raise ValueError(f"Unsupported NBS period code: {code}")


def _extract_article_text(html: str) -> str:
    match = re.search(r'<div id="zoom"[^>]*>(.*?)</div>\s*</td>', html, flags=re.S)
    body = match.group(1) if match else html
    body = re.sub(r"<br\s*/?>", "\n", body, flags=re.I)
    body = re.sub(r"</p>", "\n", body, flags=re.I)
    body = re.sub(r"<[^>]+>", "", body)
    body = body.replace("\xa0", " ")
    return re.sub(r"\s+", " ", body).strip()


def _parse_release_date_from_html(html: str) -> str | None:
    for pattern in (
        r"文章来源：\s*(\d{4}-\d{2}-\d{2})",
        r"发布时间：\s*(\d{4}-\d{2}-\d{2})",
        r'content="(\d{4}-\d{2}-\d{2})"',
    ):
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return None


def _parse_signed_chinese_amount_to_tn_yuan(text: str) -> float:
    normalized = str(text or "").replace(",", "").strip()
    sign = -1.0 if "减少" in normalized else 1.0
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(万亿元|亿元)", normalized)
    if match is None:
        raise ValueError(f"Unsupported amount text: {text}")
    value = float(match.group(1))
    if match.group(2) == "亿元":
        value = value / 10000
    return sign * value


def _parse_unsigned_chinese_amount_to_tn_yuan(text: str) -> float:
    normalized = str(text or "").replace(",", "").strip()
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(万亿元|亿元)", normalized)
    if match is None:
        raise ValueError(f"Unsupported amount text: {text}")
    value = float(match.group(1))
    if match.group(2) == "亿元":
        value = value / 10000
    return value


def _title_to_period_end(title: str) -> date | None:
    text = str(title or "").strip()
    month_match = re.search(r"(\d{4})年(\d{1,2})月", text)
    if month_match:
        return _month_end(int(month_match.group(1)), int(month_match.group(2)))
    year_match = re.search(r"(\d{4})年", text)
    if year_match is None:
        return None
    year = int(year_match.group(1))
    if "上半年" in text or "二季度" in text:
        return _quarter_end(year, 2)
    if "前三季度" in text or "三季度" in text:
        return _quarter_end(year, 3)
    if "一季度" in text:
        return _quarter_end(year, 1)
    if "四季度" in text or re.search(r"\d{4}年金融统计数据报告", text):
        return _quarter_end(year, 4)
    return None


@dataclass
class _ProviderRuntimeState:
    availability: ProviderAvailability
    detail: str


def _parse_release_date_from_html_clean(html: str) -> str | None:
    for pattern in (
        r"文章来源[:：]?\s*(\d{4}-\d{2}-\d{2})",
        r"发布时间[:：]?\s*(\d{4}-\d{2}-\d{2})",
        r'content="(\d{4}-\d{2}-\d{2})"',
    ):
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return None


def _parse_signed_amount_tn_yuan(text: str) -> float:
    normalized = str(text or "").replace(",", "").strip()
    sign = -1.0 if "减少" in normalized else 1.0
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(万亿元|亿元)", normalized)
    if match is None:
        raise ValueError(f"Unsupported amount text: {text}")
    value = float(match.group(1))
    if match.group(2) == "亿元":
        value = value / 10000
    return sign * value


def _parse_unsigned_amount_tn_yuan(text: str) -> float:
    normalized = str(text or "").replace(",", "").strip()
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(万亿元|亿元)", normalized)
    if match is None:
        raise ValueError(f"Unsupported amount text: {text}")
    value = float(match.group(1))
    if match.group(2) == "亿元":
        value = value / 10000
    return value


def _title_to_period_end_clean(title: str) -> date | None:
    text = str(title or "").strip()
    month_match = re.search(r"(\d{4})年(\d{1,2})月", text)
    if month_match:
        return _month_end(int(month_match.group(1)), int(month_match.group(2)))
    year_match = re.search(r"(\d{4})年", text)
    if year_match is None:
        return None
    year = int(year_match.group(1))
    if "上半年" in text or "二季度" in text:
        return _quarter_end(year, 2)
    if "前三季度" in text or "三季度" in text:
        return _quarter_end(year, 3)
    if "一季度" in text:
        return _quarter_end(year, 1)
    if "四季度" in text or re.search(r"\d{4}年金融统计数据报告", text):
        return _quarter_end(year, 4)
    return None


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
        ),
    }
    _SPOT_CONFIG: dict[str, dict[str, Any]] = {
        "CSI300": {"market": "cn", "code": "sh000300", "functions": ("stock_zh_index_spot_em", "stock_zh_index_spot_sina")},
        "CSI500": {"market": "cn", "code": "sh000905", "functions": ("stock_zh_index_spot_em", "stock_zh_index_spot_sina")},
        "CSI1000": {"market": "cn", "code": "sh000852", "functions": ("stock_zh_index_spot_em", "stock_zh_index_spot_sina")},
        "SSE": {"market": "cn", "code": "sh000001", "functions": ("stock_zh_index_spot_em", "stock_zh_index_spot_sina")},
        "CHINEXT": {"market": "cn", "code": "sz399006", "functions": ("stock_zh_index_spot_em", "stock_zh_index_spot_sina")},
        "HSTECH": {"market": "hk", "code": "HSTECH", "functions": ("stock_hk_index_spot_sina",)},
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
            eligible = self._augment_records_with_spot_quote(
                akshare=akshare,
                symbol=symbol,
                records=eligible,
                trade_date=trade_date,
            )
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

    def _augment_records_with_spot_quote(
        self,
        *,
        akshare,
        symbol: str,
        records: list[dict[str, Any]],
        trade_date: date,
    ) -> list[dict[str, Any]]:
        if not records:
            return records
        config = self._SPOT_CONFIG.get(symbol)
        if not config:
            return records

        latest_record = records[-1]
        if latest_record["trade_date"] >= trade_date:
            return records

        if not self._should_use_spot_session_close_for_trade_date(
            market=str(config.get("market") or ""),
            trade_date=trade_date,
        ):
            return records

        spot_quote = self._load_index_spot_quote(
            akshare=akshare,
            symbol=symbol,
            spot_code=str(config.get("code") or symbol),
            function_names=tuple(config.get("functions") or ()),
        )
        latest_price = spot_quote.get("latest_price")
        previous_close = spot_quote.get("previous_close")
        if latest_price is None or previous_close is None:
            return records

        if abs(float(previous_close) - float(latest_record["close_price"])) > 0.5:
            logger.warning(
                "Skip HK spot quote for %s because previous close %.4f does not match latest daily close %.4f",
                symbol,
                float(previous_close),
                float(latest_record["close_price"]),
            )
            return records

        return [
            *records,
            {
                "trade_date": trade_date,
                "close_price": float(latest_price),
            },
        ]

    def _should_use_spot_session_close_for_trade_date(self, *, market: str, trade_date: date) -> bool:
        shanghai_now = datetime.now(UTC).astimezone(ZoneInfo("Asia/Shanghai"))
        if trade_date != shanghai_now.date():
            return False
        minutes = shanghai_now.hour * 60 + shanghai_now.minute
        if market == "cn":
            return (11 * 60 + 30) <= minutes < (13 * 60) or minutes >= (15 * 60)
        if market == "hk":
            return (12 * 60) <= minutes < (13 * 60) or minutes >= (16 * 60 + 15)
        return False

    def _load_index_spot_quote(
        self,
        *,
        akshare,
        symbol: str,
        spot_code: str,
        function_names: Sequence[str],
    ) -> dict[str, float]:
        last_error: Exception | None = None
        for function_name in function_names:
            if not hasattr(akshare, function_name):
                continue
            try:
                frame = getattr(akshare, function_name)()
            except Exception as error:
                last_error = error
                continue
            quote = self._extract_spot_quote_from_frame(frame=frame, spot_code=spot_code)
            if quote:
                return quote
        if last_error is not None:
            logger.warning("AKShare spot quote fetch failed for %s: %s", symbol, last_error)
        return {}

    def _extract_spot_quote_from_frame(self, *, frame, spot_code: str) -> dict[str, float]:
        if frame is None or getattr(frame, "empty", True):
            return {}

        code_column = next(
            (
                column for column in frame.columns
                if str(column).strip() in {"代码", "symbol", "Symbol", "指数代码"}
            ),
            None,
        )
        if code_column is None:
            return {}

        matched = frame[frame[code_column].astype(str) == spot_code]
        if matched.empty:
            return {}

        row = matched.iloc[-1].to_dict()
        latest_price = _pick_first(row, ("最新价", "最新", "latest", "Latest", "close", "收盘"))
        previous_close = _pick_first(row, ("昨收", "previous_close", "Previous Close", "昨日收盘"))
        if latest_price is None or previous_close is None:
            return {}

        try:
            return {
                "latest_price": float(latest_price),
                "previous_close": float(previous_close),
            }
        except (TypeError, ValueError):
            return {}

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail="AKShare 市场端点已配置，可抓取宽基指数快照。",
            checked_at=_checked_at(),
        )


class OfficialMacroDataProvider:
    """Fetch macro history directly from official NBS and PBOC pages."""

    provider_key = "official-macro"
    _USER_AGENT = "ai-news-bot/1.0 (+https://github.com/giftedunicorn/ai-news-bot)"
    _NBS_URL = "https://data.stats.gov.cn/easyquery.htm"
    _PBOC_STATS_LIST_URL = "https://www.pbc.gov.cn/diaochatongjisi/116219/116225/index.html"
    _PBOC_STATS_PAGE_TEMPLATE = "https://www.pbc.gov.cn/diaochatongjisi/116219/116225/11871-{page}.html"
    _PBOC_NEWS_LIST_URL = "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html"
    _PBOC_NEWS_PAGE_TEMPLATE = "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/11040-{page}.html"
    _ANCHOR_RE = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>", re.I | re.S)
    _NBS_NOMINAL_GDP_TOTAL_CODE = "A010101"
    _NBS_REAL_GDP_TOTAL_CODE = "A010301"
    _PBOC_LOAN_BALANCE_REPORT_FALLBACKS = (
        (date(2024, 12, 31), "2024年四季度金融机构贷款投向统计报告", "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/2025092212554556296/index.html"),
        (date(2025, 3, 31), "2025年一季度金融机构贷款投向统计报告", "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/2025092212554751302/index.html"),
        (date(2025, 6, 30), "2025年二季度金融机构贷款投向统计报告", "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/2025092212554883025/index.html"),
        (date(2025, 9, 30), "2025年三季度金融机构贷款投向统计报告", "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/5877760/index.html"),
    )

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self._USER_AGENT})

    def fetch_history_series(
        self,
        *,
        indicator_codes: Sequence[str],
        start_date: date,
    ) -> Sequence[MacroIndicatorSeries]:
        requested = set(indicator_codes)
        result: dict[str, MacroIndicatorSeries] = {}
        nominal_gdp_quarter_values: list[tuple[str, date, float]] | None = None

        if "cpi" in requested:
            result["cpi"] = MacroIndicatorSeries(
                provider=self.provider_key,
                indicator_code="cpi",
                display_name="CPI",
                unit="%",
                source_url="https://data.stats.gov.cn/",
                points=tuple(self._fetch_nbs_monthly_cpi_points(start_date=start_date)),
            )
        if "ppi" in requested:
            result["ppi"] = MacroIndicatorSeries(
                provider=self.provider_key,
                indicator_code="ppi",
                display_name="PPI",
                unit="%",
                source_url="https://data.stats.gov.cn/",
                points=tuple(self._fetch_nbs_monthly_ppi_points(start_date=start_date)),
            )

        if requested & {"gdp_nominal", "gdp_real", "household_leverage", "enterprise_leverage"}:
            nominal_gdp_quarter_values = self._fetch_nbs_nominal_gdp_quarter_values(
                start_date=start_date - timedelta(days=370)
            )
            if "gdp_nominal" in requested:
                result["gdp_nominal"] = MacroIndicatorSeries(
                    provider=self.provider_key,
                    indicator_code="gdp_nominal",
                    display_name="Nominal GDP Growth",
                    unit="%",
                    source_url="https://data.stats.gov.cn/",
                    points=tuple(
                        self._build_nominal_gdp_growth_points(
                            nbs_quarter_values=nominal_gdp_quarter_values,
                            start_date=start_date,
                        )
                    ),
                )
            if "gdp_real" in requested:
                result["gdp_real"] = MacroIndicatorSeries(
                    provider=self.provider_key,
                    indicator_code="gdp_real",
                    display_name="Real GDP Growth",
                    unit="%",
                    source_url="https://data.stats.gov.cn/",
                    points=tuple(self._fetch_nbs_real_gdp_growth_points(start_date=start_date)),
                )

        if requested & {"household_new_loans", "enterprise_new_loans"}:
            household_points, enterprise_points = self._fetch_pbc_new_loan_points_v2(start_date=start_date)
            result["household_new_loans"] = MacroIndicatorSeries(
                provider=self.provider_key,
                indicator_code="household_new_loans",
                display_name="Household New Loans",
                unit="tn yuan",
                source_url=self._PBOC_STATS_LIST_URL,
                points=tuple(household_points),
            )
            result["enterprise_new_loans"] = MacroIndicatorSeries(
                provider=self.provider_key,
                indicator_code="enterprise_new_loans",
                display_name="Enterprise New Loans",
                unit="tn yuan",
                source_url=self._PBOC_STATS_LIST_URL,
                points=tuple(enterprise_points),
            )

        if requested & {"household_leverage", "enterprise_leverage"}:
            if nominal_gdp_quarter_values is None:
                nominal_gdp_quarter_values = self._fetch_nbs_nominal_gdp_quarter_values(
                    start_date=start_date - timedelta(days=370)
                )
            loan_balance_points = self._fetch_pbc_loan_balance_points_v2(start_date=start_date - timedelta(days=120))
            household_leverage, enterprise_leverage = self._build_leverage_points_v2(
                loan_balance_points=loan_balance_points,
                nbs_quarter_values=nominal_gdp_quarter_values,
                start_date=start_date,
            )
            result["household_leverage"] = MacroIndicatorSeries(
                provider=self.provider_key,
                indicator_code="household_leverage",
                display_name="Household Leverage",
                unit="%",
                source_url=self._PBOC_NEWS_LIST_URL,
                points=tuple(household_leverage),
            )
            result["enterprise_leverage"] = MacroIndicatorSeries(
                provider=self.provider_key,
                indicator_code="enterprise_leverage",
                display_name="Enterprise Leverage",
                unit="%",
                source_url=self._PBOC_NEWS_LIST_URL,
                points=tuple(enterprise_leverage),
            )

        if "usd_cny" in requested:
            try:
                result["usd_cny"] = MacroIndicatorSeries(
                    provider=self.provider_key,
                    indicator_code="usd_cny",
                    display_name="人民币兑美元中间价",
                    unit="CNY/USD",
                    source_url=self._safe_rmb_history_url(),
                    points=tuple(self._fetch_safe_usd_cny_points(start_date=start_date)),
                )
            except Exception as exc:
                logger.warning("Official macro fetch failed for usd_cny: %s", exc)

        if requested & {"gold_price", "oil_price", "copper_gold_ratio"}:
            try:
                commodity_points = self._fetch_world_bank_commodity_points(start_date=start_date - timedelta(days=40))
                if "gold_price" in requested:
                    result["gold_price"] = MacroIndicatorSeries(
                        provider=self.provider_key,
                        indicator_code="gold_price",
                        display_name="Gold",
                        unit="USD/troy oz",
                        source_url=self._world_bank_pink_sheet_url(),
                        points=tuple(commodity_points["gold_price"]),
                    )
                if "oil_price" in requested:
                    result["oil_price"] = MacroIndicatorSeries(
                        provider=self.provider_key,
                        indicator_code="oil_price",
                        display_name="WTI Crude",
                        unit="USD/bbl",
                        source_url=self._world_bank_pink_sheet_url(),
                        points=tuple(commodity_points["oil_price"]),
                    )
                if "copper_gold_ratio" in requested:
                    result["copper_gold_ratio"] = MacroIndicatorSeries(
                        provider=self.provider_key,
                        indicator_code="copper_gold_ratio",
                        display_name="Copper/Gold Ratio",
                        unit="ratio",
                        source_url=self._world_bank_pink_sheet_url(),
                        points=tuple(
                            self._build_copper_gold_ratio_points(
                                copper_points=commodity_points["copper_price"],
                                gold_points=commodity_points["gold_price"],
                                start_date=start_date,
                            )
                        ),
                    )
            except Exception as exc:
                logger.warning("Official macro fetch failed for World Bank commodities: %s", exc)

        treasury_daily_10y_points: list[MacroHistoryPoint] | None = None
        if requested & {"us_10y_yield", "us_credit_spread"}:
            try:
                treasury_daily_10y_points = self._fetch_treasury_10y_daily_points(start_date=start_date - timedelta(days=40))
                if "us_10y_yield" in requested:
                    result["us_10y_yield"] = MacroIndicatorSeries(
                        provider=self.provider_key,
                        indicator_code="us_10y_yield",
                        display_name="US 10Y Treasury",
                        unit="pct",
                        source_url="https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve",
                        points=tuple(point for point in treasury_daily_10y_points if point.period_end >= start_date),
                    )
            except Exception as exc:
                treasury_daily_10y_points = None
                logger.warning("Official macro fetch failed for us_10y_yield: %s", exc)

        if "us_credit_spread" in requested:
            try:
                treasury_monthly_10y_points = self._build_monthly_average_points(
                    points=treasury_daily_10y_points or [],
                    unit="pct",
                    source_url="https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve",
                    start_date=start_date,
                )
                hqm_points = self._fetch_treasury_hqm_10y_points(start_date=start_date - timedelta(days=370))
                result["us_credit_spread"] = MacroIndicatorSeries(
                    provider=self.provider_key,
                    indicator_code="us_credit_spread",
                    display_name="US Credit Spread",
                    unit="pct",
                    source_url="https://home.treasury.gov/data/treasury-coupon-issues-and-corporate-bond-yield-curve/corporate-bond-yield-curve",
                    points=tuple(
                        self._build_credit_spread_points(
                            corporate_points=hqm_points,
                            treasury_points=treasury_monthly_10y_points,
                            start_date=start_date,
                        )
                    ),
                )
            except Exception as exc:
                logger.warning("Official macro fetch failed for us_credit_spread: %s", exc)

        if "nvidia_stock_price" in requested:
            try:
                result["nvidia_stock_price"] = MacroIndicatorSeries(
                    provider=self.provider_key,
                    indicator_code="nvidia_stock_price",
                    display_name="NVIDIA",
                    unit="USD",
                    source_url="https://www.nasdaq.com/market-activity/stocks/nvda/historical",
                    points=tuple(self._fetch_nasdaq_stock_history_points(symbol="NVDA", start_date=start_date)),
                )
            except Exception as exc:
                logger.warning("Official macro fetch failed for nvidia_stock_price: %s", exc)

        return [result[code] for code in indicator_codes if code in result and result[code].points]

    def fetch_latest_readings(
        self,
        *,
        indicator_codes: Sequence[str],
    ) -> Sequence[MacroIndicatorReading]:
        start_date = date.today() - timedelta(days=400)
        series_items = self.fetch_history_series(indicator_codes=indicator_codes, start_date=start_date)
        readings: list[MacroIndicatorReading] = []
        for item in series_items:
            latest = item.points[-1]
            previous = item.points[-2] if len(item.points) > 1 else None
            readings.append(
                MacroIndicatorReading(
                    provider=item.provider,
                    indicator_code=item.indicator_code,
                    display_name=item.display_name,
                    value=latest.value,
                    unit=item.unit,
                    period_label=latest.period_label,
                    released_at=latest.released_at,
                    source_url=item.source_url,
                    previous_value=previous.value if previous else None,
                    change_value=(latest.value - previous.value) if previous else None,
                    change_kind="vs prior release" if previous else None,
                    trend_summary=None,
                )
            )
        return readings

    def _world_bank_pink_sheet_url(self) -> str:
        return (
            "https://thedocs.worldbank.org/en/doc/"
            "74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx"
        )

    def _safe_rmb_history_url(self) -> str:
        return "https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do"

    def _safe_rmb_export_url(self) -> str:
        return "https://www.safe.gov.cn/AppStructured/hlw/exportRMBExcel.do"

    def _fetch_safe_usd_cny_points(self, *, start_date: date) -> list[MacroHistoryPoint]:
        import pandas as pd  # type: ignore

        end_date = date.today()
        response = self._session.post(
            self._safe_rmb_export_url(),
            data={
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "queryYN": "true",
            },
            timeout=30,
            verify=False,
        )
        response.raise_for_status()
        frame = pd.read_excel(io.BytesIO(response.content))
        date_column = frame.columns[0]
        usd_column = frame.columns[1]
        points: list[MacroHistoryPoint] = []
        for _, row in frame.iterrows():
            raw_date = row.get(date_column)
            raw_value = self._coerce_numeric_field(row.get(usd_column))
            if raw_date is None or raw_value is None:
                continue
            if hasattr(raw_date, "date"):
                period_end = raw_date.date()
            elif hasattr(raw_date, "to_pydatetime"):
                period_end = raw_date.to_pydatetime().date()
            else:
                period_end = datetime.strptime(str(raw_date).strip(), "%Y-%m-%d").date()
            if period_end < start_date:
                continue
            # SAFE stores RMB midpoint as price per 100 foreign currency units.
            usd_cny = raw_value / 100
            points.append(
                MacroHistoryPoint(
                    period_end=period_end,
                    period_label=period_end.isoformat(),
                    value=round(usd_cny, 4),
                    unit="CNY/USD",
                    source_url=self._safe_rmb_history_url(),
                    released_at=period_end.isoformat(),
                )
            )
        points.sort(key=lambda item: item.period_end)
        return points

    def _fetch_world_bank_commodity_points(self, *, start_date: date) -> dict[str, list[MacroHistoryPoint]]:
        import pandas as pd  # type: ignore

        raw = pd.read_excel(self._world_bank_pink_sheet_url(), sheet_name="Monthly Prices", header=None)
        commodity_names = [str(value).strip() for value in raw.iloc[4].tolist()]
        data = raw.iloc[6:].copy()
        data.columns = ["period_code", *commodity_names[1:]]
        data = data.dropna(subset=["period_code"])

        def pick_column(name_fragment: str) -> str:
            for column in data.columns:
                if name_fragment.lower() in str(column).lower():
                    return str(column)
            raise KeyError(f"Missing World Bank commodity column containing: {name_fragment}")

        gold_column = pick_column("Gold")
        oil_column = pick_column("Crude oil, WTI")
        copper_column = pick_column("Copper")
        source_url = self._world_bank_pink_sheet_url()

        result = {
            "gold_price": [],
            "oil_price": [],
            "copper_price": [],
        }
        for _, row in data.iterrows():
            period_code = str(row["period_code"]).strip()
            match = re.fullmatch(r"(\d{4})M(\d{2})", period_code)
            if match is None:
                continue
            year = int(match.group(1))
            month = int(match.group(2))
            period_end = _month_end(year, month)
            if period_end < start_date:
                continue
            period_label = f"{year:04d}-{month:02d}"
            values = {
                "gold_price": self._coerce_numeric_field(row[gold_column]),
                "oil_price": self._coerce_numeric_field(row[oil_column]),
                "copper_price": self._coerce_numeric_field(row[copper_column]),
            }
            units = {
                "gold_price": "USD/troy oz",
                "oil_price": "USD/bbl",
                "copper_price": "USD/mt",
            }
            for code, value in values.items():
                if value is None:
                    continue
                result[code].append(
                    MacroHistoryPoint(
                        period_end=period_end,
                        period_label=period_label,
                        value=round(value, 4),
                        unit=units[code],
                        source_url=source_url,
                        released_at=period_end.isoformat(),
                    )
                )
        return result

    def _build_copper_gold_ratio_points(
        self,
        *,
        copper_points: Sequence[MacroHistoryPoint],
        gold_points: Sequence[MacroHistoryPoint],
        start_date: date,
    ) -> list[MacroHistoryPoint]:
        gold_by_period = {point.period_end: point for point in gold_points}
        points: list[MacroHistoryPoint] = []
        for copper in copper_points:
            gold = gold_by_period.get(copper.period_end)
            if gold is None or gold.value == 0:
                continue
            copper_per_lb = copper.value / 2204.6226218488
            ratio = copper_per_lb / gold.value
            if copper.period_end < start_date:
                continue
            points.append(
                MacroHistoryPoint(
                    period_end=copper.period_end,
                    period_label=copper.period_label,
                    value=round(ratio, 6),
                    unit="ratio",
                    source_url=copper.source_url,
                    released_at=copper.released_at,
                )
            )
        return points

    def _fetch_treasury_10y_daily_points(self, *, start_date: date) -> list[MacroHistoryPoint]:
        points: list[MacroHistoryPoint] = []
        seen_period_ends: set[date] = set()
        today = date.today()
        for year, month in _iter_month_starts(start_date, today):
            period_key = f"{year:04d}{month:02d}"
            url = (
                "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                f"daily-treasury-rates.csv/all/{period_key}"
                f"?field_tdr_date_value_month={period_key}&type=daily_treasury_yield_curve&page&_format=csv"
            )
            response = self._session.get(url, timeout=30)
            response.raise_for_status()
            reader = csv.DictReader(io.StringIO(response.text))
            for row in reader:
                raw_date = str(row.get("Date", "")).strip()
                raw_value = str(row.get("10 Yr", "")).strip()
                if not raw_date or not raw_value:
                    continue
                period_end = datetime.strptime(raw_date, "%m/%d/%Y").date()
                if period_end < start_date:
                    continue
                # Treasury 按月接口在测试或上游异常时可能返回重复日期，入库前按日期去重。
                if period_end in seen_period_ends:
                    continue
                value = self._coerce_numeric_field(raw_value)
                if value is None:
                    continue
                seen_period_ends.add(period_end)
                points.append(
                    MacroHistoryPoint(
                        period_end=period_end,
                        period_label=period_end.isoformat(),
                        value=round(value, 4),
                        unit="pct",
                        source_url=url,
                        released_at=period_end.isoformat(),
                    )
                )
        points.sort(key=lambda item: item.period_end)
        return points

    def _build_monthly_average_points(
        self,
        *,
        points: Sequence[MacroHistoryPoint],
        unit: str,
        source_url: str,
        start_date: date,
    ) -> list[MacroHistoryPoint]:
        monthly: dict[tuple[int, int], list[float]] = {}
        for point in points:
            monthly.setdefault((point.period_end.year, point.period_end.month), []).append(point.value)
        result: list[MacroHistoryPoint] = []
        for year_month in sorted(monthly):
            year, month = year_month
            period_end = _month_end(year, month)
            if period_end < start_date:
                continue
            values = monthly[year_month]
            result.append(
                MacroHistoryPoint(
                    period_end=period_end,
                    period_label=f"{year:04d}-{month:02d}",
                    value=round(sum(values) / len(values), 4),
                    unit=unit,
                    source_url=source_url,
                    released_at=period_end.isoformat(),
                )
            )
        return result

    def _fetch_treasury_hqm_10y_points(self, *, start_date: date) -> list[MacroHistoryPoint]:
        import pandas as pd  # type: ignore

        url = "https://home.treasury.gov/system/files/226/hqm_qh_pars.xls"
        frame = pd.read_excel(url, sheet_name="Sheet1", header=3)
        columns = list(frame.columns)
        ten_year_column = columns[4]
        points: list[MacroHistoryPoint] = []
        for _, row in frame.iterrows():
            raw_period = str(row["Date"]).strip()
            raw_value = self._coerce_numeric_field(row[ten_year_column])
            if not raw_period or raw_period.lower() == "nan" or raw_value is None:
                continue
            period_anchor = datetime.strptime(raw_period, "%b %Y").date()
            period_end = _month_end(period_anchor.year, period_anchor.month)
            if period_end < start_date:
                continue
            points.append(
                MacroHistoryPoint(
                    period_end=period_end,
                    period_label=f"{period_anchor.year:04d}-{period_anchor.month:02d}",
                    value=round(raw_value, 4),
                    unit="pct",
                    source_url=url,
                    released_at=period_end.isoformat(),
                )
            )
        return points

    def _build_credit_spread_points(
        self,
        *,
        corporate_points: Sequence[MacroHistoryPoint],
        treasury_points: Sequence[MacroHistoryPoint],
        start_date: date,
    ) -> list[MacroHistoryPoint]:
        treasury_by_period = {point.period_end: point for point in treasury_points}
        points: list[MacroHistoryPoint] = []
        for corporate in corporate_points:
            treasury = treasury_by_period.get(corporate.period_end)
            if treasury is None:
                continue
            if corporate.period_end < start_date:
                continue
            spread = corporate.value - treasury.value
            points.append(
                MacroHistoryPoint(
                    period_end=corporate.period_end,
                    period_label=corporate.period_label,
                    value=round(spread, 4),
                    unit="pct",
                    source_url=corporate.source_url,
                    released_at=corporate.released_at,
                )
            )
        return points

    def _fetch_nasdaq_stock_history_points(self, *, symbol: str, start_date: date) -> list[MacroHistoryPoint]:
        url = (
            f"https://api.nasdaq.com/api/quote/{symbol}/historical"
            f"?assetclass=stocks&fromdate={start_date.isoformat()}&limit=500&todate={date.today().isoformat()}"
        )
        source_url = f"https://www.nasdaq.com/market-activity/stocks/{symbol.lower()}/historical"
        response = self._session.get(
            url,
            headers={
                "Accept": "application/json",
                "Origin": "https://www.nasdaq.com",
                "Referer": f"https://www.nasdaq.com/market-activity/stocks/{symbol.lower()}/historical",
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        rows = (((payload.get("data") or {}).get("tradesTable") or {}).get("rows") or [])
        points: list[MacroHistoryPoint] = []
        for row in rows:
            raw_date = str(row.get("date", "")).strip()
            raw_close = str(row.get("close", "")).strip()
            if not raw_date or not raw_close:
                continue
            period_end = datetime.strptime(raw_date, "%m/%d/%Y").date()
            if period_end < start_date:
                continue
            value = self._coerce_numeric_field(raw_close)
            if value is None:
                continue
            points.append(
                MacroHistoryPoint(
                    period_end=period_end,
                    period_label=period_end.isoformat(),
                    value=round(value, 4),
                    unit="USD",
                    source_url=source_url,
                    released_at=period_end.isoformat(),
                )
            )
        points.sort(key=lambda item: item.period_end)
        return points

    def _coerce_numeric_field(self, value: Any) -> float | None:
        if value is None:
            return None
        text = str(value).strip().replace(",", "").replace("$", "")
        if not text or text.lower() in {"nan", "nd", "n/a", "бн"}:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _fetch_nbs_monthly_cpi_points(self, *, start_date: date) -> list[MacroHistoryPoint]:
        points = self._fetch_nbs_series_points(dbcode="hgyd", code="A01010G", transform=lambda value: value - 100)
        points.extend(self._fetch_nbs_series_points(dbcode="hgyd", code="A01010J", transform=lambda value: value - 100))
        points.sort(key=lambda item: item.period_end)
        return [point for point in points if point.period_end >= start_date]

    def _fetch_nbs_monthly_ppi_points(self, *, start_date: date) -> list[MacroHistoryPoint]:
        points = self._fetch_nbs_series_points(dbcode="hgyd", code="A010801", transform=lambda value: value - 100)
        return [point for point in points if point.period_end >= start_date]

    def _fetch_nbs_nominal_gdp_quarter_values(self, *, start_date: date) -> list[tuple[str, date, float]]:
        payload = self._fetch_nbs_query(dbcode="hgjd", code="A0101", period_value="LAST12")
        rows: list[tuple[str, date, float]] = []
        for node in payload["returndata"]["datanodes"]:
            if node["wds"][0]["valuecode"] != self._NBS_NOMINAL_GDP_TOTAL_CODE:
                continue
            if not node["data"]["hasdata"]:
                continue
            period_label, period_end = _parse_nbs_period_code(node["wds"][1]["valuecode"])
            rows.append((period_label, period_end, float(node["data"]["strdata"])))
        rows.sort(key=lambda item: item[1])
        return [row for row in rows if row[1] >= start_date]

    def _build_nominal_gdp_growth_points(
        self,
        *,
        nbs_quarter_values: Sequence[tuple[str, date, float]],
        start_date: date,
    ) -> list[MacroHistoryPoint]:
        points: list[MacroHistoryPoint] = []
        for index in range(4, len(nbs_quarter_values)):
            period_label, period_end, value = nbs_quarter_values[index]
            previous_value = nbs_quarter_values[index - 4][2]
            if previous_value == 0:
                continue
            growth = ((value / previous_value) - 1) * 100
            points.append(
                MacroHistoryPoint(
                    period_end=period_end,
                    period_label=period_label,
                    value=round(growth, 4),
                    unit="%",
                    source_url="https://data.stats.gov.cn/",
                    released_at=period_end.isoformat(),
                )
            )
        return [point for point in points if point.period_end >= start_date]

    def _fetch_nbs_real_gdp_growth_points(self, *, start_date: date) -> list[MacroHistoryPoint]:
        points = self._fetch_nbs_series_points(
            dbcode="hgjd",
            code="A0103",
            leaf_code=self._NBS_REAL_GDP_TOTAL_CODE,
            transform=lambda value: value - 100,
        )
        return [point for point in points if point.period_end >= start_date]

    def _fetch_nbs_query(self, *, dbcode: str, code: str, period_value: str) -> dict[str, Any]:
        response = self._session.post(
            self._NBS_URL,
            params={
                "m": "QueryData",
                "dbcode": dbcode,
                "rowcode": "zb",
                "colcode": "sj",
                "wds": "[]",
                "dfwds": json.dumps(
                    [
                        {"wdcode": "zb", "valuecode": code},
                        {"wdcode": "sj", "valuecode": period_value},
                    ],
                    ensure_ascii=False,
                ),
                "k1": str(int(datetime.now(UTC).timestamp() * 1000)),
            },
            timeout=20,
            verify=False,
        )
        response.raise_for_status()
        return response.json()

    def _fetch_nbs_series_points(
        self,
        *,
        dbcode: str,
        code: str,
        leaf_code: str | None = None,
        transform: Callable[[float], float],
    ) -> list[MacroHistoryPoint]:
        payload = self._fetch_nbs_query(dbcode=dbcode, code=code, period_value="LAST24")
        points: list[MacroHistoryPoint] = []
        for node in payload["returndata"]["datanodes"]:
            if leaf_code is not None and node["wds"][0]["valuecode"] != leaf_code:
                continue
            if not node["data"]["hasdata"]:
                continue
            period_label, period_end = _parse_nbs_period_code(node["wds"][1]["valuecode"])
            points.append(
                MacroHistoryPoint(
                    period_end=period_end,
                    period_label=period_label,
                    value=round(transform(float(node["data"]["strdata"])), 4),
                    unit="%",
                    source_url="https://data.stats.gov.cn/",
                    released_at=period_end.isoformat(),
                )
            )
        points.sort(key=lambda item: item.period_end)
        return points

    def _fetch_pbc_new_loan_points(self, *, start_date: date) -> tuple[list[MacroHistoryPoint], list[MacroHistoryPoint]]:
        report_links = self._collect_pbc_links(
            list_url=self._PBOC_STATS_LIST_URL,
            page_template=self._PBOC_STATS_PAGE_TEMPLATE,
            title_keyword="金融统计数据报告",
            start_date=date(start_date.year, 1, 1),
            max_pages=6,
        )
        cumulative_rows: list[tuple[date, float, float, str]] = []
        for period_end, _title, url in report_links:
            html = self._fetch_text(url)
            article = _extract_article_text(html)
            household_match = re.search(r"住户贷款(增加|减少)([0-9.]+(?:万亿元|亿元))", article)
            enterprise_match = re.search(r"企（事）业单位贷款(增加|减少)([0-9.]+(?:万亿元|亿元))", article)
            if household_match is None or enterprise_match is None:
                continue
            released_at = _parse_release_date_from_html(html) or period_end.isoformat()
            cumulative_rows.append(
                (
                    period_end,
                    _parse_signed_chinese_amount_to_tn_yuan("".join(household_match.groups())),
                    _parse_signed_chinese_amount_to_tn_yuan("".join(enterprise_match.groups())),
                    released_at,
                )
            )

        household_points: list[MacroHistoryPoint] = []
        enterprise_points: list[MacroHistoryPoint] = []
        rows_by_year: dict[int, list[tuple[date, float, float, str]]] = {}
        for row in cumulative_rows:
            rows_by_year.setdefault(row[0].year, []).append(row)
        for rows in rows_by_year.values():
            rows.sort(key=lambda item: item[0])
            household_previous = 0.0
            enterprise_previous = 0.0
            for period_end, household_cumulative, enterprise_cumulative, released_at in rows:
                household_value = household_cumulative - household_previous
                enterprise_value = enterprise_cumulative - enterprise_previous
                period_label = period_end.strftime("%Y-%m")
                household_points.append(
                    MacroHistoryPoint(
                        period_end=period_end,
                        period_label=period_label,
                        value=round(household_value, 4),
                        unit="tn yuan",
                        source_url=self._PBOC_STATS_LIST_URL,
                        released_at=released_at,
                    )
                )
                enterprise_points.append(
                    MacroHistoryPoint(
                        period_end=period_end,
                        period_label=period_label,
                        value=round(enterprise_value, 4),
                        unit="tn yuan",
                        source_url=self._PBOC_STATS_LIST_URL,
                        released_at=released_at,
                    )
                )
                household_previous = household_cumulative
                enterprise_previous = enterprise_cumulative

        household_points.sort(key=lambda item: item.period_end)
        enterprise_points.sort(key=lambda item: item.period_end)
        return (
            [point for point in household_points if point.period_end >= start_date],
            [point for point in enterprise_points if point.period_end >= start_date],
        )

    def _fetch_pbc_loan_balance_points(self, *, start_date: date) -> list[tuple[date, float, float, str]]:
        report_links = self._collect_pbc_links(
            list_url=self._PBOC_NEWS_LIST_URL,
            page_template=self._PBOC_NEWS_PAGE_TEMPLATE,
            title_keyword="金融机构贷款投向统计报告",
            start_date=start_date,
            max_pages=28,
        )
        rows: list[tuple[date, float, float, str]] = []
        for period_end, _title, url in report_links:
            html = self._fetch_text(url)
            article = _extract_article_text(html)
            enterprise_match = re.search(r"本外币企事业单位贷款余额([0-9.]+万亿元)", article)
            household_match = re.search(r"本外币住户贷款余额([0-9.]+万亿元)", article)
            if enterprise_match is None or household_match is None:
                continue
            released_at = _parse_release_date_from_html(html) or period_end.isoformat()
            rows.append(
                (
                    period_end,
                    _parse_unsigned_chinese_amount_to_tn_yuan(household_match.group(1)),
                    _parse_unsigned_chinese_amount_to_tn_yuan(enterprise_match.group(1)),
                    released_at,
                )
            )
        rows.sort(key=lambda item: item[0])
        return rows

    def _build_leverage_points(
        self,
        *,
        loan_balance_points: Sequence[tuple[date, float, float, str]],
        nbs_quarter_values: Sequence[tuple[str, date, float]],
        start_date: date,
    ) -> tuple[list[MacroHistoryPoint], list[MacroHistoryPoint]]:
        denominator_by_period: dict[date, float] = {}
        ordered = sorted(nbs_quarter_values, key=lambda item: item[1])
        for index in range(3, len(ordered)):
            denominator_by_period[ordered[index][1]] = sum(item[2] for item in ordered[index - 3:index + 1])

        household_points: list[MacroHistoryPoint] = []
        enterprise_points: list[MacroHistoryPoint] = []
        for period_end, household_balance, enterprise_balance, released_at in loan_balance_points:
            denominator = denominator_by_period.get(period_end)
            if not denominator:
                continue
            period_label = f"{period_end.year:04d}-Q{((period_end.month - 1) // 3) + 1}"
            household_points.append(
                MacroHistoryPoint(
                    period_end=period_end,
                    period_label=period_label,
                    value=round((household_balance * 10000 / denominator) * 100, 4),
                    unit="%",
                    source_url=self._PBOC_NEWS_LIST_URL,
                    released_at=released_at,
                )
            )
            enterprise_points.append(
                MacroHistoryPoint(
                    period_end=period_end,
                    period_label=period_label,
                    value=round((enterprise_balance * 10000 / denominator) * 100, 4),
                    unit="%",
                    source_url=self._PBOC_NEWS_LIST_URL,
                    released_at=released_at,
                )
            )
        return (
            [point for point in household_points if point.period_end >= start_date],
            [point for point in enterprise_points if point.period_end >= start_date],
        )

    def _collect_pbc_links(
        self,
        *,
        list_url: str,
        page_template: str,
        title_keyword: str,
        start_date: date,
        max_pages: int,
    ) -> list[tuple[date, str, str]]:
        collected: list[tuple[date, str, str]] = []
        seen_urls: set[str] = set()
        for page in range(1, max_pages + 1):
            url = list_url if page == 1 else page_template.format(page=page)
            html = self._fetch_text(url)
            page_min_date: date | None = None
            page_matches = 0
            for href, title in self._ANCHOR_RE.findall(html):
                if title_keyword not in title:
                    continue
                period_end = _title_to_period_end(title)
                if period_end is None:
                    continue
                page_matches += 1
                page_min_date = period_end if page_min_date is None else min(page_min_date, period_end)
                absolute_url = urljoin(url, href)
                if absolute_url in seen_urls:
                    continue
                seen_urls.add(absolute_url)
                collected.append((period_end, title, absolute_url))
            if page_matches == 0 and page > 1:
                break
            if page_min_date is not None and page_min_date < start_date:
                break
        collected.sort(key=lambda item: item[0])
        return [item for item in collected if item[0] >= start_date]

    def _fetch_text(self, url: str) -> str:
        response = self._session.get(url, timeout=20, verify=False)
        response.raise_for_status()
        response.encoding = "utf-8"
        return response.text

    def _fetch_pbc_new_loan_points_v2(
        self,
        *,
        start_date: date,
    ) -> tuple[list[MacroHistoryPoint], list[MacroHistoryPoint]]:
        report_links = self._collect_pbc_links_v2(
            list_url=self._PBOC_STATS_LIST_URL,
            page_template=self._PBOC_STATS_PAGE_TEMPLATE,
            title_keyword="金融统计数据报告",
            start_date=date(start_date.year, 1, 1),
            max_pages=6,
        )
        cumulative_rows: list[tuple[date, float, float, str]] = []
        for period_end, _title, url in report_links:
            html = self._fetch_text(url)
            article = _extract_article_text(html)
            household_match = re.search(r"住户贷款(增加|减少)([0-9.]+(?:万亿元|亿元))", article)
            enterprise_match = re.search(r"企（事）业单位贷款(增加|减少)([0-9.]+(?:万亿元|亿元))", article)
            if household_match is None or enterprise_match is None:
                continue
            released_at = _parse_release_date_from_html_clean(html) or period_end.isoformat()
            cumulative_rows.append(
                (
                    period_end,
                    _parse_signed_amount_tn_yuan("".join(household_match.groups())),
                    _parse_signed_amount_tn_yuan("".join(enterprise_match.groups())),
                    released_at,
                )
            )

        household_points: list[MacroHistoryPoint] = []
        enterprise_points: list[MacroHistoryPoint] = []
        rows_by_year: dict[int, list[tuple[date, float, float, str]]] = {}
        for row in cumulative_rows:
            rows_by_year.setdefault(row[0].year, []).append(row)
        for rows in rows_by_year.values():
            rows.sort(key=lambda item: item[0])
            household_previous = 0.0
            enterprise_previous = 0.0
            for period_end, household_cumulative, enterprise_cumulative, released_at in rows:
                period_label = period_end.strftime("%Y-%m")
                household_value = household_cumulative - household_previous
                enterprise_value = enterprise_cumulative - enterprise_previous
                household_points.append(
                    MacroHistoryPoint(
                        period_end=period_end,
                        period_label=period_label,
                        value=round(household_value, 4),
                        unit="tn yuan",
                        source_url=self._PBOC_STATS_LIST_URL,
                        released_at=released_at,
                    )
                )
                enterprise_points.append(
                    MacroHistoryPoint(
                        period_end=period_end,
                        period_label=period_label,
                        value=round(enterprise_value, 4),
                        unit="tn yuan",
                        source_url=self._PBOC_STATS_LIST_URL,
                        released_at=released_at,
                    )
                )
                household_previous = household_cumulative
                enterprise_previous = enterprise_cumulative

        household_points.sort(key=lambda item: item.period_end)
        enterprise_points.sort(key=lambda item: item.period_end)
        return (
            [point for point in household_points if point.period_end >= start_date],
            [point for point in enterprise_points if point.period_end >= start_date],
        )

    def _fetch_pbc_loan_balance_points_v2(
        self,
        *,
        start_date: date,
    ) -> list[tuple[date, float, float, str]]:
        report_links = self._collect_pbc_links_v2(
            list_url=self._PBOC_NEWS_LIST_URL,
            page_template=self._PBOC_NEWS_PAGE_TEMPLATE,
            title_keyword="金融机构贷款投向统计报告",
            start_date=start_date,
            max_pages=28,
        )
        if not report_links:
            report_links = [
                item
                for item in self._PBOC_LOAN_BALANCE_REPORT_FALLBACKS
                if item[0] >= start_date
            ]
        rows: list[tuple[date, float, float, str]] = []
        for period_end, _title, url in report_links:
            html = self._fetch_text(url)
            article = _extract_article_text(html)
            enterprise_match = re.search(r"本外币企事业单位贷款余额([0-9.]+(?:万亿元|亿元))", article)
            household_match = re.search(r"本外币住户贷款余额([0-9.]+(?:万亿元|亿元))", article)
            if enterprise_match is None or household_match is None:
                continue
            released_at = _parse_release_date_from_html_clean(html) or period_end.isoformat()
            rows.append(
                (
                    period_end,
                    _parse_unsigned_amount_tn_yuan(household_match.group(1)),
                    _parse_unsigned_amount_tn_yuan(enterprise_match.group(1)),
                    released_at,
                )
            )
        rows.sort(key=lambda item: item[0])
        return rows

    def _build_leverage_points_v2(
        self,
        *,
        loan_balance_points: Sequence[tuple[date, float, float, str]],
        nbs_quarter_values: Sequence[tuple[str, date, float]],
        start_date: date,
    ) -> tuple[list[MacroHistoryPoint], list[MacroHistoryPoint]]:
        ordered = self._quarterly_flow_values_v2(nbs_quarter_values)
        denominator_by_period: dict[date, float] = {}
        for index in range(3, len(ordered)):
            denominator_by_period[ordered[index][1]] = sum(item[2] for item in ordered[index - 3:index + 1])

        household_points: list[MacroHistoryPoint] = []
        enterprise_points: list[MacroHistoryPoint] = []
        for period_end, household_balance, enterprise_balance, released_at in loan_balance_points:
            denominator = denominator_by_period.get(period_end)
            if not denominator:
                continue
            period_label = f"{period_end.year:04d}-Q{((period_end.month - 1) // 3) + 1}"
            household_points.append(
                MacroHistoryPoint(
                    period_end=period_end,
                    period_label=period_label,
                    value=round((household_balance * 10000 / denominator) * 100, 4),
                    unit="%",
                    source_url=self._PBOC_NEWS_LIST_URL,
                    released_at=released_at,
                )
            )
            enterprise_points.append(
                MacroHistoryPoint(
                    period_end=period_end,
                    period_label=period_label,
                    value=round((enterprise_balance * 10000 / denominator) * 100, 4),
                    unit="%",
                    source_url=self._PBOC_NEWS_LIST_URL,
                    released_at=released_at,
                )
            )

        return (
            [point for point in household_points if point.period_end >= start_date],
            [point for point in enterprise_points if point.period_end >= start_date],
        )

    def _quarterly_flow_values_v2(
        self,
        nbs_quarter_values: Sequence[tuple[str, date, float]],
    ) -> list[tuple[str, date, float]]:
        ordered = sorted(nbs_quarter_values, key=lambda item: item[1])
        quarterly: list[tuple[str, date, float]] = []
        previous_by_year: dict[int, float] = {}
        for period_label, period_end, cumulative_value in ordered:
            previous_value = previous_by_year.get(period_end.year, 0.0)
            quarterly.append((period_label, period_end, cumulative_value - previous_value))
            previous_by_year[period_end.year] = cumulative_value
        return quarterly

    def _collect_pbc_links_v2(
        self,
        *,
        list_url: str,
        page_template: str,
        title_keyword: str,
        start_date: date,
        max_pages: int,
    ) -> list[tuple[date, str, str]]:
        collected: list[tuple[date, str, str]] = []
        seen_urls: set[str] = set()
        for page in range(1, max_pages + 1):
            url = list_url if page == 1 else page_template.format(page=page)
            html = self._fetch_text(url)
            page_min_date: date | None = None
            page_matches = 0
            for match in self._ANCHOR_RE.finditer(html):
                attrs = match.group("attrs") or ""
                body = match.group("body") or ""
                href_match = re.search(r'href="([^"]+)"', attrs, re.I)
                if href_match is None:
                    continue
                title_match = re.search(r'title="([^"]+)"', attrs, re.I)
                visible_title = re.sub(r"<[^>]+>", "", body)
                visible_title = unescape(visible_title).replace("\xa0", " ").strip()
                title = unescape(title_match.group(1)).strip() if title_match else visible_title
                if title_keyword not in title and title_keyword not in visible_title:
                    continue
                period_end = _title_to_period_end_clean(title)
                if period_end is None:
                    continue
                page_matches += 1
                page_min_date = period_end if page_min_date is None else min(page_min_date, period_end)
                absolute_url = urljoin(url, href_match.group(1))
                if absolute_url in seen_urls:
                    continue
                seen_urls.add(absolute_url)
                collected.append((period_end, title, absolute_url))
            if page_matches == 0 and page > 1:
                break
            if page_min_date is not None and page_min_date < start_date:
                break
        collected.sort(key=lambda item: item[0])
        return [item for item in collected if item[0] >= start_date]

    def healthcheck(self) -> ProviderStatus:
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail="Official NBS and PBOC macro endpoints are configured.",
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

    def fetch_history_series(
        self,
        *,
        indicator_codes: Sequence[str],
        start_date: date,
    ) -> Sequence[MacroIndicatorSeries]:
        _ = start_date
        series: list[MacroIndicatorSeries] = []
        for reading in self.fetch_latest_readings(indicator_codes=indicator_codes):
            period_end = date.today()
            series.append(
                MacroIndicatorSeries(
                    provider=self.provider_key,
                    indicator_code=reading.indicator_code,
                    display_name=reading.display_name,
                    unit=reading.unit,
                    source_url=reading.source_url,
                    points=(
                        MacroHistoryPoint(
                            period_end=period_end,
                            period_label=reading.period_label,
                            value=reading.value,
                            unit=reading.unit,
                            source_url=reading.source_url,
                            released_at=reading.released_at,
                        ),
                    ),
                )
            )
        return series

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

    def fetch_history_series(
        self,
        *,
        indicator_codes: Sequence[str],
        start_date: date,
    ) -> Sequence[MacroIndicatorSeries]:
        requested = list(indicator_codes)
        if self._primary_failed:
            return list(self._fallback.fetch_history_series(indicator_codes=requested, start_date=start_date))
        try:
            primary_items = list(self._primary.fetch_history_series(indicator_codes=requested, start_date=start_date))
        except Exception as exc:
            self._primary_failed = True
            logger.warning("Macro provider fallback triggered: %s", exc)
            self._set_state(
                ProviderAvailability.DEGRADED,
                f"实时宏观数据不可用（{exc}）",
            )
            return list(self._fallback.fetch_history_series(indicator_codes=requested, start_date=start_date))

        primary_by_code = {item.indicator_code: item for item in primary_items}
        missing_codes = [code for code in requested if code not in primary_by_code]
        if not missing_codes:
            self._set_state(ProviderAvailability.LIVE, f"实时宏观读数：{self._primary.provider_key}")
            return primary_items

        fallback_items = list(self._fallback.fetch_history_series(indicator_codes=missing_codes, start_date=start_date))
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
