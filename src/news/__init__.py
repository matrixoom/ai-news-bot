"""
News Module - News fetching, generation, and web search functionality
"""
from .generator import NewsGenerator
from .fetcher import NewsFetcher
from .web_search import WebSearchTool, get_search_tool_definition


__all__ = [
    'NewsGenerator',
    'NewsFetcher',
    'WebSearchTool',
    'get_search_tool_definition',
]
