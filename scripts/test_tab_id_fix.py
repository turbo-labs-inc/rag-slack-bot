"""Test that tab IDs will be stored correctly after the fix."""

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


async def test_tab_id_fix():
    """Test that tab IDs are now stored correctly."""
    print("🧪 Testing Tab ID Storage Fix")
    print("=" * 40)
    
    try:
        settings = get_settings()
        
        # Initialize components
        docs_client = GoogleDocsClient(
            service_account_path=settings.google_service_account_key_path
        )
        docs_parser = GoogleDocsParser()
        indexer = DocumentIndexer()
        
        # Fetch and parse document
        print("📥 Fetching and parsing document...")
        document = docs_client.get_document(settings.google_docs_id)
        parsed_doc = docs_parser.parse_document(document)
        
        # Check first few sections have tab IDs
        print(f"\n🔍 Checking parsed sections for tab IDs:")
        for i, section in enumerate(parsed_doc.sections[:5]):
            print(f"   Section {i+1}: '{section.title}'")
            print(f"      tab_title: '{section.tab_title}'")
            print(f"      tab_id: '{section.tab_id}'")
            
        # Test indexing a small collection
        print(f"\n📦 Testing small reindex with tab ID fix...")
        stats = await indexer.index_document(
            document=parsed_doc,
            collection_name="test_tab_id_fix",
            use_smart_chunking=False,  # Fast basic chunking
            generate_embeddings=False,  # Skip embeddings for speed
            batch_size=5,
        )
        
        print(f"✅ Indexed {stats['chunks_created']} chunks")
        
        # Check what got stored
        import chromadb
        chroma_client = chromadb.HttpClient(host="localhost", port=8000)
        collection = chroma_client.get_collection("test_tab_id_fix")
        
        result = collection.peek(limit=3)
        
        if result and 'metadatas' in result:
            print(f"\n📋 Sample stored metadata:")
            for i, metadata in enumerate(result['metadatas'][:3]):
                print(f"   Chunk {i+1}:")
                print(f"      source_tab: {metadata.get('source_tab', 'MISSING')}")
                print(f"      source_tab_id: {metadata.get('source_tab_id', 'MISSING')}")
                
                # Test URL generation
                doc_id = metadata.get('source_document_id')
                tab_id = metadata.get('source_tab_id')
                
                if doc_id and tab_id:
                    full_url = f"https://docs.google.com/document/d/{doc_id}/edit?tab={tab_id}"
                    print(f"      🎯 Full URL: {full_url}")
                elif doc_id:
                    base_url = f"https://docs.google.com/document/d/{doc_id}/edit"
                    print(f"      ⚠️  Base URL only: {base_url}")
                else:
                    print(f"      ❌ Cannot generate URL")
        
        if all(metadata.get('source_tab_id') for metadata in result['metadatas'][:3]):
            print(f"\n🎉 SUCCESS! Tab IDs are now being stored correctly!")
            print(f"   After you reindex with /gt_update, deep links will work!")
        else:
            print(f"\n❌ Tab IDs still missing - check the chunking process")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_tab_id_fix())