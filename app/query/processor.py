"""Query processing pipeline with RAG implementation."""

import logging
import re
import time
from typing import Any

from app.config import get_settings
from app.embedding import DocumentIndexer
from app.llm.base import LLMProvider, create_llm_provider
from .models import QueryContext, QueryResult, SearchResult

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Handles query processing with RAG (Retrieval Augmented Generation)."""

    def __init__(
        self,
        indexer: DocumentIndexer | None = None,
        llm_provider: LLMProvider | None = None,
        collection_name: str = "document_chunks",
    ):
        """Initialize query processor.
        
        Args:
            indexer: Document indexer for search
            llm_provider: LLM provider for response generation
            collection_name: Vector database collection name
        """
        self.indexer = indexer
        self.llm_provider = llm_provider
        self.collection_name = collection_name
        self.settings = get_settings()

    async def _ensure_providers(self) -> None:
        """Ensure all providers are initialized."""
        if self.indexer is None:
            self.indexer = DocumentIndexer()
        
        if self.llm_provider is None:
            self.llm_provider = await create_llm_provider()

    def preprocess_query(self, query: str) -> str:
        """Clean and preprocess the user query.
        
        Args:
            query: Raw user query
            
        Returns:
            Cleaned query string
        """
        # Remove extra whitespace
        query = re.sub(r'\s+', ' ', query.strip())
        
        # Remove common Slack formatting
        query = re.sub(r'<@[A-Z0-9]+>', '', query)  # Remove user mentions
        query = re.sub(r'<#[A-Z0-9]+\|[^>]+>', '', query)  # Remove channel mentions
        query = re.sub(r'<http[^>]+>', '', query)  # Remove links
        
        # Remove bot mention patterns
        query = re.sub(r'@\w+', '', query)
        
        # Clean up punctuation and formatting
        query = re.sub(r'[^\w\s\?\!\.\,\-]', ' ', query)
        query = re.sub(r'\s+', ' ', query.strip())
        
        return query

    async def search_documents(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.1,
    ) -> list[SearchResult]:
        """Search for relevant documents.
        
        Args:
            query: Search query
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of search results
        """
        await self._ensure_providers()
        
        # Search vector database
        raw_results = await self.indexer.search_documents(
            query=query,
            collection_name=self.collection_name,
            limit=limit * 2,  # Get extra results to filter
        )
        
        # Convert to SearchResult objects and filter
        search_results = []
        for result in raw_results:
            if result["similarity"] >= min_similarity:
                search_result = SearchResult(
                    content=result["content"],
                    similarity=result["similarity"],
                    metadata=result["metadata"],
                    source_section=result["metadata"].get("source_section", "Untitled Section"),
                    source_tab=result["metadata"].get("source_tab", "Untitled Tab"),
                    document_url=self._generate_doc_url(result["metadata"]),
                )
                search_results.append(search_result)
        
        # Limit to requested number
        return search_results[:limit]

    def _generate_doc_url(self, metadata: dict[str, Any]) -> str | None:
        """Generate Google Doc URL for a search result.
        
        Args:
            metadata: Chunk metadata
            
        Returns:
            Google Doc URL with tab parameter or None
        """
        doc_id = metadata.get("source_document_id")
        tab_id = metadata.get("source_tab_id")
        
        if not doc_id:
            return None
        
        # Create URL to Google Doc
        base_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        
        # Add tab parameter if available
        if tab_id:
            base_url += f"?tab={tab_id}"
        
        return base_url

    async def generate_response(
        self,
        query: str,
        search_results: list[SearchResult],
        context: QueryContext | None = None,
    ) -> str:
        """Generate response using RAG.
        
        Args:
            query: User query
            search_results: Search results from vector database
            context: Optional query context
            
        Returns:
            Generated response
        """
        await self._ensure_providers()
        
        if not search_results:
            return "I couldn't find any relevant information in the documentation to answer your question. Please try rephrasing your question or ask about a different topic."
        
        # Build context from search results
        context_parts = []
        for i, result in enumerate(search_results[:3], 1):  # Use top 3 results
            context_part = f"Source {i} (from {result.source_tab} → {result.source_section}):\n{result.content}"
            context_parts.append(context_part)
        
        context_text = "\n\n".join(context_parts)
        
        # Company context for better domain understanding
        company_context = """Gravitate is an AI-powered supply and dispatch platform specifically designed for the fuel distribution industry. The software optimizes fuel supply, in-tank inventory management, and logistics operations for convenience stores (C-stores), wholesalers, and carriers in the petroleum industry.

The platform serves the downstream segment of the U.S. petroleum industry, working with wholesale distributors, rack wholesale marketers, and retail fuel suppliers. Gravitate's solution addresses the complex challenges of fuel logistics including supply strategy optimization, automated order creation, real-time inventory monitoring, pricing engine management, carrier dispatch coordination, and delivery reconciliation. Key industry terminology includes rack pricing, bulk products, splash blending, branded vs unbranded fuel, basis pricing, spot markets, futures markets, and supply directives.

The system integrates with Automatic Tank Gauge (ATG) systems, DTN price feeds, carrier management platforms, and various data sources to provide comprehensive fuel supply chain management from terminal rack to retail site delivery."""

        # Create RAG prompt with company context
        full_prompt = f"""You are a concise AI assistant for Gravitate team members. Answer questions about our fuel distribution platform using the provided documentation.

Company Context: {company_context.split('.')[0]}. 

Documentation:
{context_text}

Guidelines:
- Answer in BULLET POINTS (2-4 bullets max)
- Use internal perspective ("our platform", "our customers")
- Each bullet should be one key fact from the documentation
- Keep bullets concise and direct
- If info is missing, briefly say so

Question: {query}

Answer:"""

        # Generate response
        response_result = await self.llm_provider.generate_response(
            prompt=full_prompt,
        )
        
        if response_result.success and response_result.response:
            return response_result.response
        else:
            logger.error(f"Failed to generate response: {response_result.error}")
            return "I encountered an error while generating a response. Please try again."

    async def process_query(
        self,
        query: str,
        context: QueryContext | None = None,
        search_limit: int = 5,
        min_similarity: float = 0.1,
    ) -> QueryResult:
        """Process a complete query with RAG pipeline.
        
        Args:
            query: User query
            context: Optional query context
            search_limit: Maximum search results
            min_similarity: Minimum similarity threshold
            
        Returns:
            Complete query result
        """
        start_time = time.time()
        
        logger.info(f"Processing query: {query}")
        
        # Step 1: Preprocess query
        cleaned_query = self.preprocess_query(query)
        logger.debug(f"Cleaned query: {cleaned_query}")
        
        # Step 2: Search for relevant documents
        search_results = await self.search_documents(
            query=cleaned_query,
            limit=search_limit,
            min_similarity=min_similarity,
        )
        
        logger.info(f"Found {len(search_results)} relevant results")
        
        # Step 3: Generate response using RAG
        answer = await self.generate_response(
            query=cleaned_query,
            search_results=search_results,
            context=context,
        )
        
        # Step 4: Calculate metrics
        processing_time = time.time() - start_time
        confidence = self._calculate_confidence(search_results)
        
        result = QueryResult(
            query=query,
            answer=answer,
            search_results=search_results,
            confidence=confidence,
            processing_time=processing_time,
            sources_used=len(search_results),
            context=context,
        )
        
        logger.info(f"Query processed in {processing_time:.2f}s with {confidence:.0%} confidence")
        return result

    def _calculate_confidence(self, search_results: list[SearchResult]) -> float:
        """Calculate confidence score based on search results.
        
        Args:
            search_results: Search results
            
        Returns:
            Confidence score between 0 and 1
        """
        if not search_results:
            return 0.0
        
        # Use top result similarity as base confidence
        top_similarity = search_results[0].similarity
        
        # Boost confidence if we have multiple good results
        good_results = len([r for r in search_results if r.similarity > 0.3])
        confidence_boost = min(good_results * 0.1, 0.3)
        
        # Cap confidence at 95%
        confidence = min(top_similarity + confidence_boost, 0.95)
        
        return max(confidence, 0.0)

    def format_for_slack(self, result: QueryResult) -> str:
        """Format query result for Slack.
        
        Args:
            result: Query result to format
            
        Returns:
            Formatted Slack message
        """
        parts = []
        
        # Main answer
        parts.append(result.answer)
        
        # Sources - group by tab and deduplicate
        if result.search_results:
            parts.append(f"\n📚 *Sources ({result.confidence:.0%} confidence):*")
            
            # Group sources by tab
            tabs_used = {}
            for source in result.search_results[:5]:  # Consider top 5 results
                tab_name = source.source_tab
                if tab_name not in tabs_used:
                    tabs_used[tab_name] = {
                        'url': source.document_url,
                        'sections': [],
                        'similarity': source.similarity
                    }
                
                # Add section if not already included
                section_name = source.source_section
                if section_name not in [s['name'] for s in tabs_used[tab_name]['sections']]:
                    tabs_used[tab_name]['sections'].append({
                        'name': section_name,
                        'similarity': source.similarity
                    })
                    
                # Update best similarity for this tab
                if source.similarity > tabs_used[tab_name]['similarity']:
                    tabs_used[tab_name]['similarity'] = source.similarity
            
            # Sort tabs by best similarity score
            sorted_tabs = sorted(tabs_used.items(), key=lambda x: x[1]['similarity'], reverse=True)
            
            # Format tab references with sections
            for tab_name, tab_info in sorted_tabs[:3]:  # Show top 3 tabs
                if tab_info['url']:
                    tab_link = f"<{tab_info['url']}|{tab_name}>"
                else:
                    tab_link = tab_name
                
                # Show sections within this tab
                section_names = [s['name'] for s in tab_info['sections'][:3]]  # Top 3 sections per tab
                if len(section_names) == 1:
                    parts.append(f"• {tab_link} → {section_names[0]}")
                else:
                    sections_text = ", ".join(section_names)
                    if len(tab_info['sections']) > 3:
                        sections_text += f" (+{len(tab_info['sections']) - 3} more)"
                    parts.append(f"• {tab_link} → {sections_text}")
        
        # Performance info (optional, for debugging)
        if result.processing_time > 2.0:
            parts.append(f"\n⏱️ _Processed in {result.processing_time:.1f}s_")
        
        return "\n".join(parts)

    async def health_check(self) -> dict[str, bool]:
        """Check health of query processing components.
        
        Returns:
            Health status dictionary
        """
        await self._ensure_providers()
        
        health = {}
        
        # Check indexer health
        indexer_health = await self.indexer.health_check()
        health.update(indexer_health)
        
        # Add query processor specific checks
        health["query_processor"] = True  # Basic initialization check
        
        health["overall"] = all(health.values())
        return health