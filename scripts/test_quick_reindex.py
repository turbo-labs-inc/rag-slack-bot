"""Quick test to reindex a few chunks and verify tab names are working."""

import asyncio
import logging

from app.config import get_settings
from app.google_docs import GoogleDocsClient, GoogleDocsParser
from app.embedding import DocumentIndexer

# Set up logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def test_quick_reindex():
    """Test reindexing to verify tab names work."""
    print("🧪 Testing Quick Reindex for Tab Names")
    print("=" * 50)
    
    try:
        settings = get_settings()
        
        # Initialize components
        docs_client = GoogleDocsClient(
            service_account_path=settings.google_service_account_key_path
        )
        docs_parser = GoogleDocsParser()
        indexer = DocumentIndexer()
        
        # Fetch and parse document
        print("📥 Fetching document...")
        document = docs_client.get_document(settings.google_docs_id)
        parsed_doc = docs_parser.parse_document(document)
        
        print(f"📑 Document: {parsed_doc.title}")
        print(f"📊 Sections: {len(parsed_doc.sections)}")
        
        # Check tab names in parsed sections
        print("\n🔍 Tab names in parsed sections:")
        tab_names = set()
        for section in parsed_doc.sections:
            if section.tab_title:
                tab_names.add(section.tab_title)
        
        for tab_name in sorted(tab_names):
            print(f"   ✅ Tab: '{tab_name}'")
        
        if not tab_names or any(name == "Untitled Tab" for name in tab_names):
            print("   ⚠️  Warning: Some tabs have fallback names")
        
        # Quick reindex with just a few chunks
        print(f"\n📦 Quick reindexing to test collection...")
        stats = await indexer.index_document(
            document=parsed_doc,
            collection_name="test_tab_names",
            use_smart_chunking=False,  # Fast basic chunking
            generate_embeddings=False,  # Skip embeddings for speed
            batch_size=5,
        )
        
        print(f"\n🎯 Results:")
        print(f"   Collection: {stats['collection_name']}")
        print(f"   Chunks: {stats['chunks_created']}")
        print(f"   Success: {stats['indexing_complete']}")
        
        # Check what got stored in vector DB
        from app.embedding.vectorizer import ChromaVectorDatabase
        vector_db = ChromaVectorDatabase()
        
        # Get collection stats
        collection_stats = await vector_db.get_collection_stats("test_tab_names")
        print(f"   Stored chunks: {collection_stats.get('total_chunks', 0)}")
        
        # Get a sample chunk to check metadata
        import chromadb
        chroma_client = chromadb.HttpClient(host="localhost", port=8000)
        collection = chroma_client.get_collection("test_tab_names")
        
        result = collection.peek(limit=3)
        
        if result and 'metadatas' in result:
            print(f"\n📋 Sample metadata:")
            for i, metadata in enumerate(result['metadatas'][:3]):
                print(f"   Chunk {i+1}:")
                print(f"      source_tab: {metadata.get('source_tab', 'N/A')}")
                print(f"      source_section: {metadata.get('source_section', 'N/A')}")
        
        print(f"\n✅ Test complete! Tab names should now be working.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_quick_reindex())