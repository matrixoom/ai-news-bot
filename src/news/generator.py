"""
AI News Generator using configurable LLM providers
"""
import os
from typing import Dict, List, Optional
from ..logger import setup_logger
from ..config import LANGUAGE_NAMES
from .web_search import WebSearchTool, get_search_tool_definition
from .fetcher import NewsFetcher
from ..llm_providers import get_llm_provider, BaseLLMProvider


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

    def generate_news_digest(
        self,
        topics: List[str],
        prompt_template: str,
        max_tokens: int = 2000,
        language: str = "en"
    ) -> str:
        """
        Generate a news digest based on provided topics.
        Uses web search tool to fetch current news when enabled.

        Args:
            topics: List of topics to cover in the news digest
            prompt_template: Template string with {topics} placeholder
            max_tokens: Maximum tokens in response
            language: Language code for the response (e.g., 'en', 'zh', 'es', 'fr', 'ja')

        Returns:
            Generated news digest as string

        Raises:
            Exception: If API call fails
        """
        try:
            # Format topics as a bulleted list
            topics_formatted = "\n".join([f"- {topic}" for topic in topics])

            # Create the full prompt
            prompt = prompt_template.format(topics=topics_formatted)

            # Add web search instruction if enabled
            if self.enable_web_search:
                prompt += "\n\nIMPORTANT: Use the web_search tool to find the most recent AI news from 2025. You can search 3-5 times with different queries to gather diverse news. After gathering news, create a comprehensive digest based on what you found."

            # Add language instruction if not English
            if language and language.lower() != "en":
                language_name = LANGUAGE_NAMES.get(language.lower(), language.upper())
                prompt += f"\n\nIMPORTANT: Please respond entirely in {language_name}."

            logger.info(f"Generating news digest with {self.provider.provider_name}, language: {language}, web_search: {self.enable_web_search}")
            logger.debug(f"Topics: {topics}")

            # Prepare messages
            messages = [{"role": "user", "content": prompt}]

            # If web search is disabled, just generate
            if not self.enable_web_search:
                return self.provider.generate(
                    messages=messages,
                    max_tokens=max_tokens
                )

            # With web search enabled, use tool calling
            tools = [get_search_tool_definition()]
            
            # Create tool handler for search
            search_count = [0]  # Use list to allow modification in closure
            max_searches = 6
            
            def tool_handler(tool_name: str, tool_input: dict, tool_use_id: str) -> str:
                """Handle tool calls for web search"""
                if tool_name == "web_search" and self.search_tool:
                    search_count[0] += 1
                    
                    if search_count[0] > max_searches:
                        return "Maximum number of searches reached. Please create the digest based on the information gathered so far."
                    
                    query = tool_input.get("query", "AI news 2025")
                    max_results = tool_input.get("max_results", 10)
                    search_results = self.search_tool.search_news(query, max_results)
                    
                    # Format search results
                    if search_results:
                        result_text = f"Search results for '{query}':\n\n"
                        for i, result in enumerate(search_results, 1):
                            result_text += f"{i}. {result['title']}\n"
                            result_text += f"   {result['snippet']}\n"
                            if result['url']:
                                result_text += f"   URL: {result['url']}\n"
                            result_text += "\n"
                        return result_text
                    else:
                        return f"No results found for '{query}'. Try a different query or proceed with the information you have."
                
                return "Tool not available"
            
            # Convert tools to appropriate format if using DeepSeek
            if self.provider.provider_name == "deepseek":
                from ..llm_providers.deepseek_provider import DeepSeekProvider
                if isinstance(self.provider, DeepSeekProvider):
                    tools = self.provider.convert_claude_tools_to_openai_format(tools)
            
            response_text = self.provider.generate_with_tools(
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
                max_iterations=8,
                tool_handler=tool_handler
            )

            logger.info("News digest generated successfully")
            logger.debug(f"Response length: {len(response_text)} characters")

            return response_text

        except Exception as e:
            logger.error(f"Failed to generate news digest: {str(e)}", exc_info=True)
            raise

    def generate_with_retry(
        self,
        topics: List[str],
        prompt_template: str,
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """
        Generate news digest with retry logic.

        Args:
            topics: List of topics to cover
            prompt_template: Template string with {topics} placeholder
            max_retries: Maximum number of retry attempts
            **kwargs: Additional arguments passed to generate_news_digest

        Returns:
            Generated news digest as string

        Raises:
            Exception: If all retries fail
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return self.generate_news_digest(topics, prompt_template, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info("Retrying...")

        logger.error(f"All {max_retries} attempts failed")
        raise last_exception

    def generate_news_digest_from_sources(
        self,
        prompt_template: str,
        max_tokens: int = 8000,
        language: str = "en",
        include_chinese: bool = True,
        max_items_per_source: int = 5
    ) -> str:
        """
        Fetch real-time news and generate a digest based on actual news articles.

        Args:
            prompt_template: Template for summarization instructions
            max_tokens: Maximum tokens in response
            language: Language code for the response
            include_chinese: Whether to include Chinese news sources
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
                include_chinese=include_chinese,
                max_items_per_source=max_items_per_source
            )

            if not news_data['international'] and not news_data['domestic']:
                logger.warning("No news items fetched, falling back to general news generation")
                # Fallback to the original method
                return self.generate_news_digest(
                    topics=["AI industry news"],
                    prompt_template=prompt_template,
                    max_tokens=max_tokens,
                    language=language
                )

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
