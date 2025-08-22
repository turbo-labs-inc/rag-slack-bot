"""Document indexing pipeline for converting chunks to vector embeddings."""

import asyncio
import logging
import time
from typing import Any

from tqdm.asyncio import tqdm

from app.chunking.models import Chunk
from app.chunking.parser import ChunkParser
from app.google_docs.parser import ParsedDocument
from app.llm.base import LLMProvider
from app.llm.factory import create_embedding_provider
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
            self.llm_provider = create_embedding_provider()

        if self.chunk_parser is None:
            self.chunk_parser = ChunkParser(
                use_smart_chunking=True,  # Use smart chunking by default
                max_chunk_size=1000,
                overlap_size=100,
            )

    async def index_document(
        self,
        document: ParsedDocument,
        collection_name: str = "office_documents",
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

        print(f"🚀 Starting document indexing")
        print(f"📋 Document: {document.title}")
        print(f"📂 Collection: {collection_name}")
        print(f"🔧 Smart chunking: {use_smart_chunking}")
        print(f"🔢 Generate embeddings: {generate_embeddings}")
        print(f"📦 Batch size: {batch_size}")
        print("=" * 60)

        logger.info(f"Starting document indexing for: {document.title}")

        # Step 1: Create chunks
        print("📝 Step 1/3: Creating document chunks...")
        logger.info("Creating document chunks...")
        if use_smart_chunking:
            self.chunk_parser.use_smart_chunking = True

        chunks = await self.chunk_parser.chunk_document(document, self.llm_provider)
        print(f"✅ Created {len(chunks)} chunks from {len(document.sections)} sections")
        logger.info(f"Created {len(chunks)} chunks")

        # Step 2: Generate embeddings
        if generate_embeddings:
            print(f"\n🔢 Step 2/3: Generating embeddings...")
            chunks_with_embeddings = await self._generate_embeddings_batch(chunks, batch_size)
        else:
            print(f"\n⏭️  Step 2/3: Skipping embedding generation")
            chunks_with_embeddings = chunks

        # Step 3: Create collection and store in vector database
        print(f"\n💾 Step 3/3: Storing chunks in vector database...")
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
        print(f"✅ Stored {len(chunks_with_embeddings)} chunks in collection: {collection_name}")

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

        print("\n" + "=" * 60)
        print("🎉 Document indexing completed successfully!")
        print(f"📋 Document: {document.title}")
        print(f"📂 Collection: {collection_name}")
        print(f"📊 Statistics:")
        print(f"   • Chunks created: {final_stats['chunks_created']}")
        print(f"   • Chunks with embeddings: {final_stats['chunks_with_embeddings']}")
        print(f"   • Chunks stored: {final_stats['chunks_stored']}")
        print(f"   • Success rate: {final_stats['chunks_with_embeddings']/final_stats['chunks_created']*100:.1f}%")
        print("=" * 60)

        logger.info(f"Document indexing completed: {final_stats['chunks_stored']} chunks stored")
        return final_stats

    async def _generate_embeddings_batch(
        self, chunks: list[Chunk], batch_size: int = 10
    ) -> list[Chunk]:
        """Generate embeddings for chunks in batches with progress tracking."""
        chunks_with_embeddings = []
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        
        print(f"🔢 Generating embeddings for {len(chunks)} chunks in {total_batches} batches...")
        
        # Create progress bar for batches
        batch_progress = tqdm(
            total=total_batches,
            desc="📦 Processing batches",
            unit="batch",
            ncols=100
        )
        
        # Create progress bar for individual chunks
        chunk_progress = tqdm(
            total=len(chunks),
            desc="📄 Processing chunks",
            unit="chunk",
            ncols=100
        )
        
        start_time = time.time()
        successful_embeddings = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            batch_num = i // batch_size + 1
            
            batch_progress.set_description(f"📦 Batch {batch_num}/{total_batches}")
            
            # Process batch concurrently
            embedding_tasks = [self._generate_chunk_embedding(chunk) for chunk in batch]
            batch_results = await asyncio.gather(*embedding_tasks, return_exceptions=True)

            # Collect successful results
            for j, (chunk, result) in enumerate(zip(batch, batch_results)):
                chunk_idx = i + j + 1
                
                if isinstance(result, Exception):
                    logger.warning(f"Failed to generate embedding for chunk {chunk_idx}: {result}")
                    chunk_progress.set_description(f"📄 Chunk {chunk_idx}/{len(chunks)} ❌ Error")
                    chunks_with_embeddings.append(chunk)  # Add without embedding
                else:
                    chunk.embedding = result
                    successful_embeddings += 1
                    chunk_progress.set_description(f"📄 Chunk {chunk_idx}/{len(chunks)} ✅ Done")
                    chunks_with_embeddings.append(chunk)
                
                # Log individual chunk progress
                if chunk.metadata and chunk.metadata.source_section:
                    section_name = chunk.metadata.source_section[:30]
                    tab_name = chunk.metadata.source_tab[:20] if chunk.metadata.source_tab else "Unknown"
                    logger.info(f"✅ Chunk {chunk_idx}/{len(chunks)}: {tab_name} → {section_name}...")
                
                chunk_progress.update(1)
            
            batch_progress.update(1)
            
            # Log batch completion with timing
            elapsed = time.time() - start_time
            chunks_per_second = (i + len(batch)) / elapsed if elapsed > 0 else 0
            logger.info(f"📦 Batch {batch_num}/{total_batches} complete - {chunks_per_second:.1f} chunks/sec")

        batch_progress.close()
        chunk_progress.close()
        
        total_time = time.time() - start_time
        final_rate = len(chunks) / total_time if total_time > 0 else 0
        
        print(f"🎉 Embedding generation complete!")
        print(f"   ✅ Successfully generated: {successful_embeddings}/{len(chunks)} embeddings")
        print(f"   ⏱️  Total time: {total_time:.1f}s ({final_rate:.1f} chunks/sec)")
        print(f"   🚀 Using {self.llm_provider.__class__.__name__}")

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
        collection_name: str = "office_documents",
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

    async def get_indexing_stats(self, collection_name: str = "office_documents") -> dict[str, Any]:
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
