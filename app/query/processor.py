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
        collection_name: str = "office_documents",
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
                # Handle both Office document and Google Docs metadata formats
                metadata = result["metadata"]
                
                # For Office documents, use document_name and path
                if "document_name" in metadata:
                    source_section = metadata.get("document_name", "Unknown Document")
                    source_tab = metadata.get("path", "").strip("/") or "Documents"
                else:
                    # For Google Docs, use original fields
                    source_section = metadata.get("source_section", "Untitled Section")
                    source_tab = metadata.get("source_tab", "Untitled Tab")
                
                search_result = SearchResult(
                    content=result["content"],
                    similarity=result["similarity"],
                    metadata=result["metadata"],
                    source_section=source_section,
                    source_tab=source_tab,
                    document_url=self._generate_doc_url(result["metadata"]),
                )
                search_results.append(search_result)
        
        # Limit to requested number
        return search_results[:limit]

    def _generate_doc_url(self, metadata: dict[str, Any]) -> str | None:
        """Generate document URL for a search result.
        
        Args:
            metadata: Chunk metadata
            
        Returns:
            Document URL (Google Docs/Drive) or None
        """
        # Handle both Office document and Google Docs metadata
        doc_id = metadata.get("source_document_id") or metadata.get("document_id")
        tab_id = metadata.get("source_tab_id")
        
        if not doc_id:
            return None
        
        # Check if it's a Google Docs document (has tab_id)
        if tab_id:
            # Google Docs with specific tab
            base_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            base_url += f"?tab=t.{tab_id}"
        else:
            # Could be either Google Docs without tabs or Drive file
            # Try to determine based on document ID pattern or metadata
            if len(doc_id) > 20:  # Google Doc IDs are typically long
                # Assume it's a Google Doc
                base_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            else:
                # Generic Google Drive file
                base_url = f"https://drive.google.com/file/d/{doc_id}/view"
        
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
        for i, result in enumerate(search_results[:3], 1):  # Use top 3 most relevant results for focus
            # Clean source reference
            source = result.source_tab if result.source_tab else "Document"
            section = f" - {result.source_section}" if result.source_section else ""
            context_part = f"[{source}{section}]:\n{result.content[:500]}"  # Limit context length
            context_parts.append(context_part)
        
        context_text = "\n---\n".join(context_parts)
        
        # Create RAG prompt for concise, high-quality answers
        full_prompt = f"""You are a concise technical assistant. Answer based ONLY on the provided documentation.

Documentation:
{context_text}

User Question: {query}

Instructions:
- Give a direct, actionable answer
- Use bullet points for steps
- Keep response under 3-4 sentences unless listing steps
- Cite source document names in parentheses
- If information is incomplete, say so briefly

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
        """Format query result for Slack with proper markdown.
        
        Args:
            result: Query result to format
            
        Returns:
            Formatted Slack message with mrkdwn
        """
        parts = []
        
        # Main answer - format with proper Slack markdown
        answer = result.answer
        # Bold important terms in the answer if they're in backticks or quotes
        answer = answer.replace('`', '*')  # Convert code ticks to bold
        parts.append(answer)
        
        # Sources section with better formatting
        if result.search_results:
            parts.append(f"\n*📚 Sources* _{result.confidence:.0%} confidence_")
            parts.append("")  # Empty line for spacing
            
            # Track unique documents/files
            seen_docs = {}
            
            for source in result.search_results[:5]:  # Top 5 results
                # Get document name and create unique key
                doc_name = source.source_tab or "Document"
                section_name = source.source_section or ""
                
                # Clean up document name (remove .docx extensions for cleaner display)
                if doc_name.endswith('.docx'):
                    doc_name = doc_name[:-5]
                elif doc_name.endswith('.doc'):
                    doc_name = doc_name[:-4]
                
                # Create document key for deduplication
                doc_key = doc_name
                
                if doc_key not in seen_docs:
                    seen_docs[doc_key] = {
                        'url': source.document_url,
                        'sections': [],
                        'best_similarity': source.similarity,
                        'full_name': doc_name
                    }
                
                # Add section if unique and relevant
                if section_name and section_name not in seen_docs[doc_key]['sections']:
                    seen_docs[doc_key]['sections'].append(section_name)
                
                # Track best similarity
                if source.similarity > seen_docs[doc_key]['best_similarity']:
                    seen_docs[doc_key]['best_similarity'] = source.similarity
            
            # Sort by similarity and format as bullet points
            sorted_docs = sorted(seen_docs.items(), key=lambda x: x[1]['best_similarity'], reverse=True)
            
            for doc_key, doc_info in sorted_docs[:4]:  # Show top 4 documents
                # Create hyperlink if URL exists
                if doc_info['url']:
                    doc_link = f"<{doc_info['url']}|{doc_info['full_name']}>"
                else:
                    doc_link = f"*{doc_info['full_name']}*"
                
                # Format confidence percentage
                confidence_pct = f"({doc_info['best_similarity']:.0%})"
                
                # Build the source line
                if doc_info['sections']:
                    # Show first 2 sections
                    sections_to_show = doc_info['sections'][:2]
                    sections_text = " → " + ", ".join(f"_{s}_" for s in sections_to_show)
                    if len(doc_info['sections']) > 2:
                        sections_text += f" _+{len(doc_info['sections']) - 2} more_"
                    parts.append(f"• {doc_link} {confidence_pct}{sections_text}")
                else:
                    parts.append(f"• {doc_link} {confidence_pct}")
        
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