"""Validation script for vector database integration and document indexing."""

import asyncio
from pathlib import Path

from app.config import get_settings
from app.embedding import DocumentIndexer
from app.google_docs import GoogleDocsClient, GoogleDocsParser


async def test_vector_database():
    """Test the complete vector database integration pipeline."""
    print("🔧 Testing Vector Database Integration")
    print("=" * 50)

    # Get settings
    settings = get_settings()
    print(f"📋 Using LLM Provider: {settings.llm_provider}")
    print(f"📋 ChromaDB URL: {settings.chroma_url}")
    print(f"📋 Document ID: {settings.google_docs_id}")
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

        # Fetch and parse document (use subset for testing)
        print("📄 Fetching and parsing document...")
        credentials_path = Path("credentials/google-docs-service-account.json")
        docs_client = GoogleDocsClient(service_account_path=credentials_path)
        docs_parser = GoogleDocsParser()

        document = docs_client.get_document(settings.google_docs_id)
        parsed_doc = docs_parser.parse_document(document)

        # Use only first few sections for testing
        test_sections = parsed_doc.sections[:5]  # Limit to first 5 sections
        test_doc = type(parsed_doc)(
            title=f"{parsed_doc.title} (Test Sample)",
            document_id=parsed_doc.document_id,
            sections=test_sections,
        )

        print(f"✅ Using {len(test_sections)} sections for testing")
        print(f"   Total characters: {len(test_doc.get_full_text())}")
        print()

        # Index document
        print("🗂️  Indexing document with vector embeddings...")
        collection_name = "test_document_chunks"

        indexing_stats = await indexer.index_document(
            document=test_doc,
            collection_name=collection_name,
            use_smart_chunking=True,
            generate_embeddings=True,
            batch_size=5,  # Small batch for testing
        )

        print("✅ Document indexing completed!")
        print(f"   Collection: {indexing_stats['collection_name']}")
        print(f"   Chunks created: {indexing_stats['chunks_created']}")
        print(f"   Chunks with embeddings: {indexing_stats['chunks_with_embeddings']}")
        print(f"   Chunks stored: {indexing_stats['chunks_stored']}")
        print()

        # Show chunk statistics
        chunk_stats = indexing_stats["chunk_statistics"]
        print("📊 Chunk Statistics:")
        print(f"   Average size: {chunk_stats['average_chunk_size']} chars")
        print(
            f"   Size range: {chunk_stats['min_chunk_size']}-{chunk_stats['max_chunk_size']} chars"
        )
        print(f"   Chunks with questions: {chunk_stats['chunks_with_questions']}")
        print(f"   Chunks with summaries: {chunk_stats['chunks_with_summaries']}")
        print(f"   Unique sections: {chunk_stats['unique_sections']}")
        print()

        # Test search functionality
        print("🔍 Testing search functionality...")
        test_queries = [
            "What is supply and dispatch?",
            "How does pricing work?",
            "Features of the system",
            "Fuel delivery management",
        ]

        for query in test_queries:
            print(f"   Query: '{query}'")
            try:
                results = await indexer.search_documents(
                    query=query, collection_name=collection_name, limit=3
                )

                print(f"   Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    similarity = result["similarity"]
                    section = result["metadata"].get("source_section", "Unknown")
                    preview = result["content"][:100].replace("\n", " ")
                    print(f"     {i}. Similarity: {similarity:.3f} | Section: {section}")
                    print(f"        Preview: {preview}...")

                    if result["metadata"].get("summary"):
                        print(f"        Summary: {result['metadata']['summary']}")
                print()

            except Exception as e:
                print(f"   ❌ Search failed: {e}")
                print()

        # Get final collection statistics
        print("📈 Final Collection Statistics:")
        final_stats = await indexer.get_indexing_stats(collection_name)

        print(f"   Collection: {final_stats['name']}")
        print(f"   Total chunks: {final_stats['total_chunks']}")
        print(f"   Chunks with questions: {final_stats.get('chunks_with_questions', 'N/A')}")
        print(f"   Unique tabs: {final_stats.get('unique_tabs', 'N/A')}")
        print(f"   Unique sections: {final_stats.get('unique_sections', 'N/A')}")
        print(f"   Average content length: {final_stats.get('average_content_length', 'N/A')}")
        print(f"   Average tokens: {final_stats.get('average_tokens', 'N/A')}")
        print()

        print("🎉 Vector database integration test completed successfully!")
        print()
        print("💡 Next steps:")
        print("   1. Try different search queries")
        print("   2. Test with metadata filters")
        print("   3. Index the full document for production use")
        print(f"   4. Collection '{collection_name}' is ready for querying")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_vector_database())
