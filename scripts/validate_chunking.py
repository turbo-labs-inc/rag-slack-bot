"""Test script to demonstrate document chunking functionality."""

import asyncio
from pathlib import Path

from app.chunking import ChunkParser
from app.config import get_settings
from app.google_docs import GoogleDocsClient, GoogleDocsParser
from app.llm.base import create_llm_provider


async def test_chunking():
    """Test the document chunking functionality."""
    print("🔧 Testing Document Chunking System")
    print("=" * 50)

    # Get settings
    settings = get_settings()
    print(f"📋 Using LLM Provider: {settings.llm_provider}")
    print(f"📋 Document ID: {settings.google_docs_id}")
    print()

    # Create clients
    credentials_path = Path("credentials/google-docs-service-account.json")
    docs_client = GoogleDocsClient(service_account_path=credentials_path)
    docs_parser = GoogleDocsParser()

    try:
        # Fetch and parse document
        print("📄 Fetching document...")
        document = docs_client.get_document(settings.google_docs_id)
        parsed_doc = docs_parser.parse_document(document)

        print(f"✅ Parsed {len(parsed_doc.sections)} sections")
        print(f"   Total characters: {len(parsed_doc.get_full_text())}")
        print()

        # Test basic chunking
        print("🧩 Testing Basic Chunking Strategy")
        print("-" * 30)

        basic_parser = ChunkParser(use_smart_chunking=False, max_chunk_size=800, overlap_size=100)

        basic_chunks = await basic_parser.chunk_document(parsed_doc)
        basic_stats = basic_parser.get_chunk_statistics(basic_chunks)

        print(f"✅ Created {len(basic_chunks)} chunks")
        print(f"   Average size: {basic_stats['average_chunk_size']} chars")
        print(
            f"   Size range: {basic_stats['min_chunk_size']}-{basic_stats['max_chunk_size']} chars"
        )
        print(f"   Questions found: {basic_stats['chunks_with_questions']}")
        print(f"   Unique sections: {basic_stats['unique_sections']}")
        print()

        # Show sample chunks
        print("📝 Sample Basic Chunks:")
        for i, chunk in enumerate(basic_chunks[:3]):
            print(f"   Chunk {i + 1} ({len(chunk.content)} chars):")
            print(f"   Section: {chunk.metadata.source_section if chunk.metadata else 'Unknown'}")
            preview = chunk.content[:100].replace("\n", " ")
            print(f"   Preview: {preview}...")
            print()

        # Test smart chunking with LLM
        print("🤖 Testing Smart Chunking Strategy")
        print("-" * 30)

        try:
            llm_provider = await create_llm_provider()

            # Test LLM connection first
            health_check = await llm_provider.health_check()
            if not health_check:
                print("⚠️  LLM provider health check failed, skipping smart chunking")
                return

            smart_parser = ChunkParser(
                use_smart_chunking=True, max_chunk_size=1200, overlap_size=150
            )

            # Use only first few sections for testing to avoid long LLM calls
            test_sections = parsed_doc.sections[:3]
            test_doc = type(parsed_doc)(
                title=parsed_doc.title, document_id=parsed_doc.document_id, sections=test_sections
            )

            print(f"🧠 Processing {len(test_sections)} sections with LLM assistance...")
            smart_chunks = await smart_parser.chunk_document(test_doc, llm_provider)
            smart_stats = smart_parser.get_chunk_statistics(smart_chunks)

            print(f"✅ Created {len(smart_chunks)} smart chunks")
            print(f"   Average size: {smart_stats['average_chunk_size']} chars")
            print(
                f"   Size range: {smart_stats['min_chunk_size']}-{smart_stats['max_chunk_size']} chars"
            )
            print(f"   Chunks with summaries: {smart_stats['chunks_with_summaries']}")
            print()

            # Show sample smart chunks with summaries
            print("📝 Sample Smart Chunks:")
            for i, chunk in enumerate(smart_chunks[:2]):
                print(f"   Chunk {i + 1} ({len(chunk.content)} chars):")
                print(
                    f"   Section: {chunk.metadata.source_section if chunk.metadata else 'Unknown'}"
                )
                if chunk.summary:
                    print(f"   Summary: {chunk.summary}")
                preview = chunk.content[:100].replace("\n", " ")
                print(f"   Preview: {preview}...")
                print()

        except Exception as e:
            print(f"⚠️  Smart chunking failed: {e}")
            print("   This is expected if LLM is not available")

        # Test embedding generation
        print("🔢 Testing Embedding Generation")
        print("-" * 30)

        try:
            llm_provider = await create_llm_provider()
            test_text = basic_chunks[0].content if basic_chunks else "Test text"

            embedding_result = await llm_provider.generate_embedding(test_text)

            if embedding_result.success:
                print(f"✅ Generated embedding with {len(embedding_result.embedding)} dimensions")
                print(f"   Model: {embedding_result.model}")
                print(f"   First 5 values: {embedding_result.embedding[:5]}")
            else:
                print(f"❌ Embedding generation failed: {embedding_result.error}")

        except Exception as e:
            print(f"⚠️  Embedding test failed: {e}")

        print()
        print("🎉 Chunking test completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_chunking())
