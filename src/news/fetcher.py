"""
News fetcher module - Fetches real-time AI news from various sources
"""
import requests
from typing import List, Dict, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
from ..logger import setup_logger


logger = setup_logger(__name__)


class NewsFetcher:
    """Fetch real-time AI news from RSS feeds and news APIs"""

    # TODO: add news sources base on the language
    def __init__(self):
        """Initialize the news fetcher"""
        # RSS feed sources for AI news (reliable sources only)
        self.rss_feeds = {
            # Major Tech Media
            "TechCrunch AI": "https://techcrunch.com/tag/artificial-intelligence/feed/",
            "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
            "MIT Technology Review": "https://www.technologyreview.com/feed/",
            "Ars Technica AI": "https://arstechnica.com/tag/ai/feed/",
            "Wired AI": "https://www.wired.com/feed/tag/ai/latest/rss",
            "The Next Web": "https://thenextweb.com/feed",
            "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            "Engadget AI": "https://www.engadget.com/tag/ai/rss.xml",

            # Official AI Company Blogs
            "OpenAI Blog": "https://openai.com/blog/rss/",
            "Google AI Blog": "https://blog.google/technology/ai/rss/",
            "DeepMind Blog": "https://deepmind.google/blog/rss.xml",
            "Meta AI Blog": "https://ai.meta.com/blog/rss/",
            "Microsoft AI Blog": "https://blogs.microsoft.com/ai/feed/",

            # Research & Academic
            "arXiv AI": "https://rss.arxiv.org/rss/cs.AI",
            "arXiv Machine Learning": "https://rss.arxiv.org/rss/cs.LG",
            "arXiv Computer Vision": "https://rss.arxiv.org/rss/cs.CV",
            "arXiv NLP": "https://rss.arxiv.org/rss/cs.CL",

            # Industry Verticals
            "Healthcare IT News AI": "https://www.healthcareitnews.com/taxonomy/term/31/feed",
            "Robotics Business Review": "https://www.roboticsbusinessreview.com/feed/",
            "Autonomous Vehicle News": "https://www.autonomousvehicleinternational.com/feed",
        }

        # Chinese AI news sources
        self.chinese_feeds = {
            "Google News AI (CN)": "https://news.google.com/rss/search?q=人工智能+AI&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
            "Google News Tech (CN)": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtcG9HZ0pEVGlnQVAB?hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
            "Google News LLM (CN)": "https://news.google.com/rss/search?q=大模型+GPT+Claude&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
            "Google News Robotics (CN)": "https://news.google.com/rss/search?q=机器人+自动驾驶&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        }

        # Japanese AI news sources
        self.japanese_feeds = {
            "Google News AI (JP)": "https://news.google.com/rss/search?q=人工知能+AI&hl=ja&gl=JP&ceid=JP:ja-JP",
            "Google News Tech (JP)": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtcG9HZ0pEVGlnQVAB?hl=ja&gl=JP&ceid=JP:ja-JP",
            "Google News LLM (JP)": "https://news.google.com/rss/search?q=大模型+GPT+Claude&hl=ja&gl=JP&ceid=JP:ja-JP",
            "Google News Robotics (JP)": "https://news.google.com/rss/search?q=ロボット+自動運転&hl=ja&gl=JP&ceid=JP:ja-JP",
        }

        # French AI news sources
        self.french_feeds = {
            "Google News AI (FR)": "https://news.google.com/rss/search?q=intelligence+artificielle+AI&hl=fr&gl=FR&ceid=FR:fr-FR",
            "Google News Tech (FR)": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtcG9HZ0pEVGlnQVAB?hl=fr&gl=FR&ceid=FR:fr-FR",
            "Google News LLM (FR)": "https://news.google.com/rss/search?q=grand+modèle+GPT+Claude&hl=fr&gl=FR&ceid=FR:fr-FR",
            "Google News Robotics (FR)": "https://news.google.com/rss/search?q=robot+autonomie&hl=fr&gl=FR&ceid=FR:fr-FR",
        }


    def fetch_rss_feed(self, feed_url: str, max_items: int = 10) -> List[Dict[str, str]]:
        """
        Fetch news items from an RSS feed.

        Args:
            feed_url: URL of the RSS feed
            max_items: Maximum number of items to fetch

        Returns:
            List of news items with title, link, description, and published date
        """
        try:
            logger.info(f"Fetching RSS feed: {feed_url}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(feed_url, headers=headers, timeout=10)
            response.raise_for_status()

            # Parse XML
            root = ET.fromstring(response.content)

            items = []
            # Handle both RSS 2.0 and Atom formats
            if root.tag == 'rss':
                news_items = root.findall('.//item')[:max_items]
                for item in news_items:
                    title = item.find('title')
                    link = item.find('link')
                    description = item.find('description')
                    pub_date = item.find('pubDate')

                    items.append({
                        'title': title.text if title is not None else '',
                        'link': link.text if link is not None else '',
                        'description': self._clean_html(description.text if description is not None else ''),
                        'published': pub_date.text if pub_date is not None else '',
                    })
            else:
                # Atom format
                namespace = {'atom': 'http://www.w3.org/2005/Atom'}
                entries = root.findall('.//atom:entry', namespace)[:max_items]
                for entry in entries:
                    title = entry.find('atom:title', namespace)
                    link = entry.find('atom:link', namespace)
                    summary = entry.find('atom:summary', namespace)
                    updated = entry.find('atom:updated', namespace)

                    items.append({
                        'title': title.text if title is not None else '',
                        'link': link.get('href', '') if link is not None else '',
                        'description': self._clean_html(summary.text if summary is not None else ''),
                        'published': updated.text if updated is not None else '',
                    })

            logger.info(f"Fetched {len(items)} items from RSS feed")
            return items

        except Exception as e:
            logger.error(f"Failed to fetch RSS feed {feed_url}: {str(e)}")
            return []

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text"""
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text).strip()

    def fetch_recent_news(
        self,
        language: str = "en",
        max_items_per_source: int = 5
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Fetch recent AI news from all configured sources.

        Args:
            language: Language code for the response
            max_items_per_source: Maximum items to fetch per source

        Returns:
            Dictionary with 'international' and 'domestic' news lists
        """
        logger.info("Fetching recent AI news from all sources...")

        all_news = {
            'international': [],
            'domestic': []
        }

        # Fetch international news
        for source_name, feed_url in self.rss_feeds.items():
            items = self.fetch_rss_feed(feed_url, max_items_per_source)
            for item in items:
                item['source'] = source_name
                all_news['international'].append(item)

        # Fetch domestic news
        if language == "zh":
            feeds = self.chinese_feeds
        elif language == "ja":
            feeds = self.japanese_feeds
        elif language == "fr":
            feeds = self.french_feeds
        else:
            logger.error(f"Unsupported language: {language}")
            return all_news

        for source_name, feed_url in feeds.items():
            items = self.fetch_rss_feed(feed_url, max_items_per_source)
            for item in items:
                item['source'] = source_name
                all_news['domestic'].append(item)

        logger.info(
            f"Fetched {len(all_news['international'])} international news items "
            f"and {len(all_news['domestic'])} domestic ({language}) news items"
        )

        return all_news

    def format_news_for_summary(self, news_data: Dict[str, List[Dict[str, str]]]) -> str:
        """
        Format fetched news into a text suitable for AI summarization.

        Args:
            news_data: Dictionary with 'international' and 'domestic' news lists

        Returns:
            Formatted news text
        """
        formatted = "# Recent AI News Items to Summarize\n\n"

        if news_data['international']:
            formatted += "## International News\n\n"
            for i, item in enumerate(news_data['international'], 1):
                formatted += f"### {i}. {item['title']}\n"
                formatted += f"**Source:** {item['source']}\n"
                if item['description']:
                    formatted += f"**Description:** {item['description'][:300]}...\n"
                formatted += f"**Link:** {item['link']}\n"
                if item['published']:
                    formatted += f"**Published:** {item['published']}\n"
                formatted += "\n"

        if news_data['domestic']:
            formatted += "## Domestic News\n\n"
            for i, item in enumerate(news_data['domestic'], 1):
                formatted += f"### {i}. {item['title']}\n"
                formatted += f"**Source:** {item['source']}\n"
                if item['description']:
                    formatted += f"**Description:** {item['description'][:300]}...\n"
                formatted += f"**Link:** {item['link']}\n"
                if item['published']:
                    formatted += f"**Published:** {item['published']}\n"
                formatted += "\n"

        return formatted
