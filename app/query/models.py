"""Query processing models and data structures."""

from dataclasses import dataclass
from typing import Any


@dataclass
class QueryContext:
    """Context information for a query."""
    
    user_id: str
    channel_id: str | None = None
    conversation_history: list[str] | None = None
    timestamp: str | None = None


@dataclass
class SearchResult:
    """Individual search result from vector database."""
    
    content: str
    similarity: float
    metadata: dict[str, Any]
    source_section: str
    source_tab: str
    document_url: str | None = None


@dataclass
class QueryResult:
    """Complete result of query processing."""
    
    query: str
    answer: str
    search_results: list[SearchResult]
    confidence: float
    processing_time: float
    sources_used: int
    context: QueryContext | None = None