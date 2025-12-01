"""
AI News Generator using configurable LLM providers
"""
from typing import List, Optional
from ..logger import setup_logger
from ..config import LANGUAGE_NAMES
from .web_search import WebSearchTool, get_search_tool_definition
from .fetcher import NewsFetcher
from ..llm_providers import get_llm_provider


logger = setup_logger(__name__)


class NewsGenerator:
    """Generate AI news digest using configurable LLM providers"""

    def __init__(
        self,
        provider_name: str = "claude",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enable_web_search: bool = False
    ):
        """
        Initialize the NewsGenerator.

        Args:
            provider_name: Name of LLM provider to use ('claude' or 'deepseek')
            api_key: API key for the provider. If None, will read from environment
            model: Model name to use. If None, uses provider's default model
            enable_web_search: Whether to enable web search tool for fetching current news

        Raises:
            ValueError: If provider is not recognized or API key is not provided
        """
        # Initialize LLM provider
        self.provider = get_llm_provider(
            provider_name=provider_name,
            api_key=api_key,
            model=model
        )

        self.enable_web_search = enable_web_search
        self.search_tool = WebSearchTool() if enable_web_search else None
        self.news_fetcher = NewsFetcher()
        logger.info(
            f"NewsGenerator initialized with {self.provider.provider_name} "
            f"(model: {self.provider.model}, web_search: {enable_web_search})"
        )

    def generate_news_digest_from_sources(
        self,
        prompt_template: str,
        max_tokens: int = 8000,
        language: str = "en",
        max_items_per_source: int = 5
    ) -> str:
        """
        Fetch real-time news and generate a digest based on actual news articles.

        Args:
            prompt_template: Template for summarization instructions
            max_tokens: Maximum tokens in response
            language: Language code for the response
            max_items_per_source: Maximum items to fetch per source

        Returns:
            Generated news digest as string

        Raises:
            Exception: If fetching or generation fails
        """
        try:
            # Fetch real-time news
            logger.info("Fetching real-time AI news from sources...")
            news_data = self.news_fetcher.fetch_recent_news(
                max_items_per_source=max_items_per_source
            )

            if not news_data['international'] and not news_data['domestic']:
                error_msg = "No news items fetched from RSS sources. Please check your network connection or RSS feed availability."
                logger.error(error_msg)
                raise Exception(error_msg)

            # Format news for summarization
            formatted_news = self.news_fetcher.format_news_for_summary(news_data)

            # Create summarization prompt
            summarization_prompt = f"""You are a senior AI industry analyst. Based on the following recent AI news articles, create a comprehensive, in-depth news digest.

{formatted_news}

Instructions:
{prompt_template}

CRITICAL REQUIREMENTS:
- SELECT 15-20 HIGH-QUALITY news items from all the items provided above
- Balance coverage across different categories (LLM, Agents, Research, Products, etc.)
- Include both international and domestic news when available
- Prioritize: groundbreaking research, major product launches, significant policy changes, large funding rounds
- Prefer primary sources (official blogs, research papers) over secondary reporting
- Avoid duplicate or overly similar news items

CONTENT DEPTH REQUIREMENTS:
- Each news summary should be 4-6 sentences
- Include: what happened, technical details, why it matters, potential implications
- Include specific numbers, metrics, and data when available
- Maintain accuracy - only include information from the provided articles

FORMATTING REQUIREMENTS:
- Format the output in clean, readable markdown with category headers
- Include source attributions as clickable markdown links: [Source Name](URL)
- Use the **Link:** field from each news item to create the clickable source link
- Example: "Source: [TechCrunch](https://techcrunch.com/article-url)" or "来源: [网站名称](URL)"
"""

            # Add language instruction if not English
            if language and language.lower() != "en":
                language_name = LANGUAGE_NAMES.get(language.lower(), language.upper())
                summarization_prompt += f"\n\nIMPORTANT: Please respond entirely in {language_name}."

            logger.info(f"Generating summary from {len(news_data['international']) + len(news_data['domestic'])} news items")

            # Use provider to generate response
            messages = [{"role": "user", "content": summarization_prompt}]
            response_text = self.provider.generate(
                messages=messages,
                max_tokens=max_tokens
            )

            logger.info("News digest generated successfully from real sources")
            logger.debug(f"Response length: {len(response_text)} characters")

            return response_text

        except Exception as e:
            logger.error(f"Failed to generate news digest from sources: {str(e)}", exc_info=True)
            raise
