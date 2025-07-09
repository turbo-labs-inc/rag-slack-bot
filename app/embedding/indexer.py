"""Document indexing pipeline for converting chunks to vector embeddings."""

import asyncio
import logging
from typing import Any

from app.chunking.models import Chunk
from app.chunking.parser import ChunkParser
from app.google_docs.parser import ParsedDocument
from app.llm.base import LLMProvider, create_llm_provider
from .vectorizer import VectorDatabase, ChromaVectorDatabase

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Pipeline for indexing documents into vector database."""

    def __init__(
        self,
        vector_db: VectorDatabase | None = None,
        llm_provider: LLMProvider | None = None,
        chunk_parser: ChunkParser | None = None,
    ):
        """Initialize document indexer.

        Args:
            vector_db: Vector database instance (creates ChromaDB if None)
            llm_provider: LLM provider for embeddings (creates from config if None)
            chunk_parser: Chunk parser (creates basic parser if None)
        """
        self.vector_db = vector_db
        self.llm_provider = llm_provider
        self.chunk_parser = chunk_parser

    async def _ensure_providers(self) -> None:
        """Ensure all providers are initialized."""
        if self.vector_db is None:
            self.vector_db = ChromaVectorDatabase()

        if self.llm_provider is None:
            self.llm_provider = await create_llm_provider()

        if self.chunk_parser is None:
            self.chunk_parser = ChunkParser(
                use_smart_chunking=True,  # Use smart chunking by default
                max_chunk_size=1000,
                overlap_size=100,
            )

    async def index_document(
        self,
        document: ParsedDocument,
        collection_name: str = "document_chunks",
        use_smart_chunking: bool = True,
        generate_embeddings: bool = True,
        batch_size: int = 10,
    ) -> dict[str, Any]:
        """Index a parsed document into the vector database.

        Args:
            document: Parsed document to index
            collection_name: Name of the vector database collection
            use_smart_chunking: Whether to use LLM-assisted chunking
            generate_embeddings: Whether to generate embeddings for chunks
            batch_size: Batch size for embedding generation

        Returns:
            Dictionary with indexing statistics
        """
        await self._ensure_providers()

        logger.info(f"Starting document indexing for: {document.title}")

        # Step 1: Create chunks
        logger.info("Creating document chunks...")
        if use_smart_chunking:
            self.chunk_parser.use_smart_chunking = True

        chunks = await self.chunk_parser.chunk_document(document, self.llm_provider)
        logger.info(f"Created {len(chunks)} chunks")

        # Step 2: Generate embeddings
        if generate_embeddings:
            logger.info("Generating embeddings for chunks...")
            chunks_with_embeddings = await self._generate_embeddings_batch(chunks, batch_size)
        else:
            chunks_with_embeddings = chunks

        # Step 3: Create collection and store in vector database
        logger.info(f"Storing chunks in collection: {collection_name}")
        collection_metadata = {
            "document_id": document.document_id,
            "document_title": document.title,
            "total_sections": len(document.sections),
            "chunk_count": len(chunks_with_embeddings),
            "indexing_strategy": "smart" if use_smart_chunking else "basic",
        }

        await self.vector_db.create_collection(collection_name, collection_metadata)
        await self.vector_db.add_chunks(collection_name, chunks_with_embeddings)

        # Step 4: Get final statistics
        stats = await self.vector_db.get_collection_stats(collection_name)
        chunk_stats = self.chunk_parser.get_chunk_statistics(chunks_with_embeddings)

        final_stats = {
            "document_title": document.title,
            "document_id": document.document_id,
            "collection_name": collection_name,
            "indexing_complete": True,
            "chunks_created": len(chunks),
            "chunks_with_embeddings": len([c for c in chunks_with_embeddings if c.embedding]),
            "chunks_stored": stats.get("total_chunks", 0),
            "chunk_statistics": chunk_stats,
            "collection_statistics": stats,
        }

        logger.info(f"Document indexing completed: {final_stats['chunks_stored']} chunks stored")
        return final_stats

    async def _generate_embeddings_batch(
        self, chunks: list[Chunk], batch_size: int = 10
    ) -> list[Chunk]:
        """Generate embeddings for chunks in batches."""
        chunks_with_embeddings = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            logger.info(
                f"Processing embedding batch {i // batch_size + 1}/{(len(chunks) + batch_size - 1) // batch_size}"
            )

            # Process batch concurrently
            embedding_tasks = [self._generate_chunk_embedding(chunk) for chunk in batch]

            batch_results = await asyncio.gather(*embedding_tasks, return_exceptions=True)

            # Collect successful results
            for chunk, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to generate embedding for chunk: {result}")
                    chunks_with_embeddings.append(chunk)  # Add without embedding
                else:
                    chunk.embedding = result
                    chunks_with_embeddings.append(chunk)

        successful_embeddings = len([c for c in chunks_with_embeddings if c.embedding])
        logger.info(f"Generated {successful_embeddings}/{len(chunks)} embeddings successfully")

        return chunks_with_embeddings

    async def _generate_chunk_embedding(self, chunk: Chunk) -> list[float] | None:
        """Generate embedding for a single chunk."""
        try:
            # Use chunk content, including summary if available
            text_to_embed = chunk.content
            if chunk.summary:
                text_to_embed = f"{chunk.summary}\n\n{chunk.content}"

            result = await self.llm_provider.generate_embedding(text_to_embed)

            if result.success and result.embedding:
                return result.embedding
            else:
                logger.warning(f"Embedding generation failed: {result.error}")
                return None

        except Exception as e:
            logger.warning(f"Exception during embedding generation: {e}")
            return None

    async def search_documents(
        self,
        query: str,
        collection_name: str = "document_chunks",
        limit: int = 10,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for relevant document chunks.

        Args:
            query: Search query text
            collection_name: Collection to search in
            limit: Maximum number of results
            metadata_filter: Optional metadata filters

        Returns:
            List of search results with content and metadata
        """
        await self._ensure_providers()

        # Generate embedding for query
        logger.info(f"Searching for: {query}")
        query_result = await self.llm_provider.generate_embedding(query)

        if not query_result.success or not query_result.embedding:
            raise RuntimeError(f"Failed to generate query embedding: {query_result.error}")

        # Search vector database
        results = await self.vector_db.search(
            collection_name=collection_name,
            query_embedding=query_result.embedding,
            limit=limit,
            metadata_filter=metadata_filter,
        )

        logger.info(f"Found {len(results)} results for query")
        return results

    async def get_indexing_stats(self, collection_name: str = "document_chunks") -> dict[str, Any]:
        """Get statistics about indexed documents.

        Args:
            collection_name: Collection to get stats for

        Returns:
            Dictionary with collection statistics
        """
        await self._ensure_providers()
        return await self.vector_db.get_collection_stats(collection_name)

    async def health_check(self) -> dict[str, bool]:
        """Check health of all components.

        Returns:
            Dictionary with health status of each component
        """
        await self._ensure_providers()

        health_status = {
            "vector_database": await self.vector_db.health_check(),
            "llm_provider": await self.llm_provider.health_check(),
        }

        health_status["overall"] = all(health_status.values())
        return health_status
