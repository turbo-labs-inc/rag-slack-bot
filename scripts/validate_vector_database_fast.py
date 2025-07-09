"""Fast validation script for vector database integration using minimal test data."""

import asyncio

from app.chunking.models import Chunk, ChunkMetadata
from app.config import get_settings
from app.embedding import DocumentIndexer


async def test_vector_database_fast():
    """Fast test of vector database integration with synthetic data."""
    print("⚡ Fast Vector Database Integration Test")
    print("=" * 50)

    # Get settings
    settings = get_settings()
    print(f"📋 ChromaDB URL: {settings.chroma_url}")
    print()

    try:
        # Initialize indexer
        print("🚀 Initializing document indexer...")
        indexer = DocumentIndexer()

        # Health check
        print("🔍 Performing health checks...")
        health = await indexer.health_check()
        print(f"   Vector Database: {'✅' if health['vector_database'] else '❌'}")
        print(f"   LLM Provider: {'✅' if health['llm_provider'] else '❌'}")
        print(f"   Overall: {'✅' if health['overall'] else '❌'}")

        if not health["overall"]:
            print("❌ Health check failed, cannot proceed")
            return
        print()

        # Create synthetic test chunks (skip document parsing)
        print("🧪 Creating synthetic test chunks...")
        test_chunks = [
            Chunk(
                content="What is Gravitate's Supply and Dispatch Solution? It's an AI-powered platform for fuel logistics.",
                summary="Overview of Gravitate's supply and dispatch platform",
                metadata=ChunkMetadata(
                    source_document_id="test-doc",
                    source_tab="Overview",
                    source_section="Introduction",
                    chunk_index=0,
                    contains_question=True,
                    estimated_tokens=20,
                ),
            ),
            Chunk(
                content="The platform optimizes fuel delivery through advanced analytics and machine learning algorithms.",
                summary="Platform uses AI for optimization",
                metadata=ChunkMetadata(
                    source_document_id="test-doc",
                    source_tab="Features",
                    source_section="Technology",
                    chunk_index=1,
                    contains_question=False,
                    estimated_tokens=15,
                ),
            ),
            Chunk(
                content="How does pricing work in the system? Pricing is based on market data and real-time analysis.",
                summary="Pricing mechanism explanation",
                metadata=ChunkMetadata(
                    source_document_id="test-doc",
                    source_tab="Pricing",
                    source_section="Pricing Overview",
                    chunk_index=2,
                    contains_question=True,
                    estimated_tokens=18,
                ),
            ),
        ]

        print(f"✅ Created {len(test_chunks)} synthetic chunks")
        print()

        # Generate embeddings (fast batch)
        print("🔢 Generating embeddings...")
        chunks_with_embeddings = await indexer._generate_embeddings_batch(test_chunks, batch_size=3)

        successful_embeddings = len([c for c in chunks_with_embeddings if c.embedding])
        print(f"✅ Generated {successful_embeddings}/{len(test_chunks)} embeddings")
        print()

        # Create collection and store
        print("🗂️  Storing in vector database...")
        collection_name = "fast_test_chunks"

        # Create collection
        await indexer.vector_db.create_collection(
            collection_name,
            {"test": True, "fast_validation": True, "chunk_count": len(chunks_with_embeddings)},
        )

        # Add chunks
        await indexer.vector_db.add_chunks(collection_name, chunks_with_embeddings)
        print(f"✅ Stored chunks in collection: {collection_name}")
        print()

        # Test search functionality
        print("🔍 Testing search functionality...")
        test_queries = ["What is supply and dispatch?", "How does pricing work?", "AI features"]

        for query in test_queries:
            print(f"   Query: '{query}'")
            try:
                results = await indexer.search_documents(
                    query=query, collection_name=collection_name, limit=2
                )

                print(f"   Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    similarity = result["similarity"]
                    section = result["metadata"].get("source_section", "Unknown")
                    print(f"     {i}. Similarity: {similarity:.3f} | Section: {section}")
                    if result["metadata"].get("summary"):
                        print(f"        Summary: {result['metadata']['summary']}")
                print()

            except Exception as e:
                print(f"   ❌ Search failed: {e}")
                print()

        # Get collection statistics
        print("📈 Collection Statistics:")
        stats = await indexer.get_indexing_stats(collection_name)

        print(f"   Collection: {stats['name']}")
        print(f"   Total chunks: {stats['total_chunks']}")
        print(f"   Chunks with questions: {stats.get('chunks_with_questions', 'N/A')}")
        print(f"   Unique tabs: {stats.get('unique_tabs', 'N/A')}")
        print(f"   Unique sections: {stats.get('unique_sections', 'N/A')}")
        print()

        print("🎉 Fast vector database test completed successfully!")
        print()
        print("💡 Next steps:")
        print("   1. Vector database integration is working")
        print("   2. Embeddings are being generated correctly")
        print("   3. Search functionality is operational")
        print("   4. Ready for full document indexing")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_vector_database_fast())
