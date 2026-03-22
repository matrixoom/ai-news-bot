"""NewsNow source registry mirrored from upstream shared/sources.json.

The list intentionally tracks active, non-redirect source IDs so the provider
can pull all available feeds through NewsNow's `/api/s` endpoint.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class NewsNowSource:
    """One upstream NewsNow source definition."""

    source_id: str
    column: str
    source_type: str
    interval_ms: int


# Synced from https://github.com/ourongxing/newsnow (shared/sources.json).
NEWSNOW_ACTIVE_SOURCE_SPECS: Tuple[NewsNowSource, ...] = (
    NewsNowSource("36kr-quick", "tech", "realtime", 600000),
    NewsNowSource("36kr-renqi", "tech", "hottest", 600000),
    NewsNowSource("baidu", "china", "hottest", 600000),
    NewsNowSource("bilibili-hot-search", "china", "hottest", 600000),
    NewsNowSource("bilibili-hot-video", "china", "hottest", 600000),
    NewsNowSource("bilibili-ranking", "china", "hottest", 1800000),
    NewsNowSource("cankaoxiaoxi", "world", "none", 1800000),
    NewsNowSource("chongbuluo-hot", "china", "hottest", 1800000),
    NewsNowSource("chongbuluo-latest", "china", "none", 1800000),
    NewsNowSource("cls-depth", "finance", "none", 600000),
    NewsNowSource("cls-hot", "finance", "hottest", 600000),
    NewsNowSource("cls-telegraph", "finance", "realtime", 300000),
    NewsNowSource("coolapk", "tech", "hottest", 600000),
    NewsNowSource("douban", "china", "hottest", 600000),
    NewsNowSource("douyin", "china", "hottest", 600000),
    NewsNowSource("fastbull-express", "finance", "realtime", 120000),
    NewsNowSource("fastbull-news", "finance", "none", 1800000),
    NewsNowSource("freebuf", "china", "hottest", 600000),
    NewsNowSource("gelonghui", "finance", "realtime", 120000),
    NewsNowSource("github-trending-today", "tech", "hottest", 600000),
    NewsNowSource("hackernews", "tech", "hottest", 600000),
    NewsNowSource("hupu", "china", "hottest", 600000),
    NewsNowSource("ifeng", "china", "hottest", 600000),
    NewsNowSource("iqiyi-hot-ranklist", "china", "hottest", 1800000),
    NewsNowSource("ithome", "tech", "realtime", 600000),
    NewsNowSource("jin10", "finance", "realtime", 600000),
    NewsNowSource("juejin", "tech", "hottest", 600000),
    NewsNowSource("kaopu", "world", "none", 1800000),
    NewsNowSource("kuaishou", "china", "hottest", 600000),
    NewsNowSource("mktnews-flash", "finance", "none", 120000),
    NewsNowSource("nowcoder", "china", "hottest", 600000),
    NewsNowSource("pcbeta-windows11", "tech", "realtime", 300000),
    NewsNowSource("producthunt", "tech", "hottest", 600000),
    NewsNowSource("qqvideo-tv-hotsearch", "china", "hottest", 1800000),
    NewsNowSource("solidot", "tech", "none", 3600000),
    NewsNowSource("sputniknewscn", "world", "none", 600000),
    NewsNowSource("sspai", "tech", "hottest", 600000),
    NewsNowSource("steam", "world", "hottest", 600000),
    NewsNowSource("tencent-hot", "china", "hottest", 1800000),
    NewsNowSource("thepaper", "china", "hottest", 1800000),
    NewsNowSource("tieba", "china", "hottest", 600000),
    NewsNowSource("toutiao", "china", "hottest", 600000),
    NewsNowSource("v2ex-share", "tech", "none", 600000),
    NewsNowSource("wallstreetcn-hot", "finance", "hottest", 1800000),
    NewsNowSource("wallstreetcn-news", "finance", "none", 1800000),
    NewsNowSource("wallstreetcn-quick", "finance", "realtime", 300000),
    NewsNowSource("weibo", "china", "hottest", 120000),
    NewsNowSource("xueqiu-hotstock", "finance", "hottest", 120000),
    NewsNowSource("zaobao", "world", "realtime", 1800000),
    NewsNowSource("zhihu", "china", "hottest", 600000),
)


NEWSNOW_SOURCE_DISPLAY_NAMES: dict[str, str] = {
    "36kr-quick": "36氪",
    "36kr-renqi": "36氪",
    "baidu": "百度热搜",
    "bilibili-hot-search": "哔哩哔哩热搜",
    "bilibili-hot-video": "哔哩哔哩热门视频",
    "bilibili-ranking": "哔哩哔哩排行榜",
    "cankaoxiaoxi": "参考消息",
    "chongbuluo-hot": "虫部落热搜",
    "chongbuluo-latest": "虫部落",
    "cls-depth": "财联社",
    "cls-hot": "财联社",
    "cls-telegraph": "财联社电报",
    "coolapk": "酷安",
    "douban": "豆瓣",
    "douyin": "抖音",
    "fastbull-express": "FastBull 快讯",
    "fastbull-news": "FastBull",
    "freebuf": "FreeBuf",
    "gelonghui": "格隆汇",
    "github-trending-today": "GitHub Trending",
    "hackernews": "Hacker News",
    "hupu": "虎扑",
    "ifeng": "凤凰网",
    "iqiyi-hot-ranklist": "爱奇艺热榜",
    "ithome": "IT之家",
    "jin10": "金十数据",
    "juejin": "稀土掘金",
    "kaopu": "靠谱新闻",
    "kuaishou": "快手",
    "mktnews-flash": "市场资讯快讯",
    "nowcoder": "牛客",
    "pcbeta-windows11": "PCBeta",
    "producthunt": "Product Hunt",
    "qqvideo-tv-hotsearch": "腾讯视频热搜",
    "solidot": "Solidot",
    "sputniknewscn": "Sputnik 中文网",
    "sspai": "少数派",
    "steam": "Steam",
    "tencent-hot": "腾讯热搜",
    "thepaper": "澎湃新闻",
    "tieba": "百度贴吧",
    "toutiao": "今日头条",
    "v2ex-share": "V2EX",
    "wallstreetcn-hot": "华尔街见闻",
    "wallstreetcn-news": "华尔街见闻",
    "wallstreetcn-quick": "华尔街见闻快讯",
    "weibo": "微博热搜",
    "xueqiu-hotstock": "雪球热股",
    "zaobao": "联合早报",
    "zhihu": "知乎热榜",
}


def display_name_for_source(source_id: str) -> str:
    """Return a user-facing media name for one NewsNow source id."""
    if source_id in NEWSNOW_SOURCE_DISPLAY_NAMES:
        return NEWSNOW_SOURCE_DISPLAY_NAMES[source_id]
    return source_id.replace("-", " ").replace("_", " ").title()
