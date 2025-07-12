"""Check what metadata is actually stored in the vector database."""

import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def check_vector_metadata():
    """Check metadata stored in vector database."""
    print("🔍 Checking Vector Database Metadata")
    print("=" * 50)
    
    try:
        # Get collection directly
        import chromadb
        chroma_client = chromadb.HttpClient(host="localhost", port=8000)
        collection = chroma_client.get_collection("document_chunks")
        
        # Get a few sample documents
        result = collection.peek(limit=5)
        
        if result and 'metadatas' in result:
            print(f"📋 Sample metadata from vector database:")
            for i, (doc, metadata) in enumerate(zip(result['documents'], result['metadatas'])):
                print(f"\n🔖 Chunk {i+1}:")
                print(f"   Content: {doc[:50]}...")
                print(f"   source_tab: {metadata.get('source_tab', 'MISSING')}")
                print(f"   source_tab_id: {metadata.get('source_tab_id', 'MISSING')}")
                print(f"   source_section: {metadata.get('source_section', 'MISSING')}")
                print(f"   source_document_id: {metadata.get('source_document_id', 'MISSING')}")
                
                # Test URL generation
                doc_id = metadata.get('source_document_id')
                tab_id = metadata.get('source_tab_id')
                
                if doc_id and tab_id:
                    full_url = f"https://docs.google.com/document/d/{doc_id}/edit?tab={tab_id}"
                    print(f"   Generated URL: {full_url}")
                elif doc_id:
                    base_url = f"https://docs.google.com/document/d/{doc_id}/edit"
                    print(f"   Base URL (no tab): {base_url}")
                else:
                    print(f"   ❌ Cannot generate URL - missing doc_id")
        
        # Test our actual query processing
        print(f"\n🧪 Testing Query Processing:")
        from app.query.processor import QueryProcessor
        
        processor = QueryProcessor()
        results = await processor.search_documents("demand forecasting", limit=3)
        
        print(f"📊 Found {len(results)} search results:")
        for i, result in enumerate(results):
            print(f"\n📄 Result {i+1}:")
            print(f"   source_tab: {result.source_tab}")
            print(f"   source_section: {result.source_section}")
            print(f"   document_url: {result.document_url}")
            
    except Exception as e:
        print(f"❌ Check failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_vector_metadata())