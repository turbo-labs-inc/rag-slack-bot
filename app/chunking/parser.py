"""Document chunking parser for processing parsed documents into chunks."""

from typing import Any

from app.google_docs.parser import ParsedDocument
from app.llm.base import LLMProvider, create_llm_provider
from .models import Chunk
from .strategies import ChunkingStrategy, BasicChunkingStrategy, SmartChunkingStrategy


class ChunkParser:
    """Main parser for chunking documents using different strategies."""

    def __init__(
        self,
        strategy: ChunkingStrategy | None = None,
        use_smart_chunking: bool = False,
        max_chunk_size: int = 1000,
        overlap_size: int = 100,
    ):
        """Initialize the chunk parser.

        Args:
            strategy: Custom chunking strategy to use
            use_smart_chunking: Whether to use LLM-assisted smart chunking
            max_chunk_size: Maximum characters per chunk
            overlap_size: Characters to overlap between chunks
        """
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.use_smart_chunking = use_smart_chunking

        if strategy:
            self.strategy = strategy
        elif use_smart_chunking:
            # Will be initialized when LLM provider is available
            self.strategy = None
        else:
            self.strategy = BasicChunkingStrategy(
                max_chunk_size=max_chunk_size, overlap_size=overlap_size
            )

    async def chunk_document(
        self, document: ParsedDocument, llm_provider: LLMProvider | None = None
    ) -> list[Chunk]:
        """Chunk a parsed document into smaller pieces.

        Args:
            document: Parsed document to chunk
            llm_provider: Optional LLM provider for smart chunking

        Returns:
            List of chunks with metadata
        """
        # Initialize smart chunking strategy if needed
        if self.use_smart_chunking and self.strategy is None:
            if llm_provider is None:
                llm_provider = await create_llm_provider()

            self.strategy = SmartChunkingStrategy(
                llm_provider=llm_provider,
                max_chunk_size=self.max_chunk_size,
                overlap_size=self.overlap_size,
            )

        # Fallback to basic strategy if smart chunking setup failed
        if self.strategy is None:
            self.strategy = BasicChunkingStrategy(
                max_chunk_size=self.max_chunk_size, overlap_size=self.overlap_size
            )

        chunks = await self.strategy.chunk_document(document)

        # Post-process chunks
        return self._post_process_chunks(chunks)

    def _post_process_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Post-process chunks for consistency and validation."""
        processed_chunks = []

        for i, chunk in enumerate(chunks):
            # Skip empty chunks
            if not chunk.content.strip():
                continue

            # Update chunk index if metadata exists
            if chunk.metadata:
                chunk.metadata.chunk_index = len(processed_chunks)

            # Ensure reasonable chunk size
            if len(chunk.content) > self.max_chunk_size * 1.5:
                print(f"⚠️  Warning: Chunk {i} exceeds size limit ({len(chunk.content)} chars)")

            processed_chunks.append(chunk)

        # Update total chunk count
        for chunk in processed_chunks:
            if chunk.metadata:
                chunk.metadata.total_chunks = len(processed_chunks)

        return processed_chunks

    def get_chunk_statistics(self, chunks: list[Chunk]) -> dict[str, Any]:
        """Get statistics about the chunked document.

        Args:
            chunks: List of document chunks

        Returns:
            Dictionary with chunk statistics
        """
        if not chunks:
            return {"total_chunks": 0}

        total_chars = sum(len(chunk.content) for chunk in chunks)
        total_words = sum(chunk.get_word_count() for chunk in chunks)
        total_tokens = sum(chunk.get_token_count() for chunk in chunks)

        chunk_sizes = [len(chunk.content) for chunk in chunks]

        # Count chunks with questions
        question_chunks = sum(
            1 for chunk in chunks if chunk.metadata and chunk.metadata.contains_question
        )

        # Count chunks with summaries
        summarized_chunks = sum(1 for chunk in chunks if chunk.summary)

        return {
            "total_chunks": len(chunks),
            "total_characters": total_chars,
            "total_words": total_words,
            "estimated_tokens": total_tokens,
            "average_chunk_size": total_chars // len(chunks),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "chunks_with_questions": question_chunks,
            "chunks_with_summaries": summarized_chunks,
            "unique_sections": len(
                set(
                    chunk.metadata.source_section
                    for chunk in chunks
                    if chunk.metadata and chunk.metadata.source_section
                )
            ),
            "unique_tabs": len(
                set(
                    chunk.metadata.source_tab
                    for chunk in chunks
                    if chunk.metadata and chunk.metadata.source_tab
                )
            ),
        }
