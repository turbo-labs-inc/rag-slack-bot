"""Script to inspect what's stored in the vector database."""

import asyncio
import json
import logging

from app.config import get_settings
from app.embedding.vectorizer import ChromaVectorDatabase

# Set up logging - silence httpx spam but keep our logs
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def inspect_vector_db():
    """Inspect the vector database contents."""
    print("🔍 Inspecting Vector Database Contents")
    print("=" * 60)
    
    try:
        # Initialize vector database
        vector_db = ChromaVectorDatabase()
        
        # Get collection stats
        collection_name = "document_chunks"
        stats = await vector_db.get_collection_stats(collection_name)
        
        print(f"📊 Collection Statistics:")
        print(f"   Collection: {collection_name}")
        print(f"   Total chunks: {stats.get('total_chunks', 0)}")
        print(f"   Metadata: {stats.get('metadata', {})}")
        print()
        
        # Get a few sample chunks to inspect metadata
        print("📋 Sample Chunks (first 5):")
        print("-" * 40)
        
        # Try to get the collection directly to inspect structure
        try:
            import chromadb
            chroma_client = chromadb.HttpClient(host="localhost", port=8000)
            collection = chroma_client.get_collection(collection_name)
            
            # Get a few documents without doing similarity search
            result = collection.peek(limit=5)
            
            if result and 'documents' in result:
                for i, (doc, metadata) in enumerate(zip(result['documents'], result.get('metadatas', []))):
                    print(f"\n🔖 Chunk {i+1}:")
                    print(f"   Content (first 100 chars): {doc[:100]}...")
                    print(f"   Metadata:")
                    for key, value in (metadata or {}).items():
                        print(f"      {key}: {value}")
            else:
                print("No documents found in collection")
                
        except Exception as e:
            print(f"Failed to peek at collection: {e}")
            # Fallback: try with correct embedding dimension (768 for Gemini)
            sample_results = await vector_db.search(
                collection_name=collection_name,
                query_embedding=[0.1] * 768,  # Try 768 dimensions
                limit=5
            )
        
        for i, result in enumerate(sample_results, 1):
            print(f"\n🔖 Chunk {i}:")
            print(f"   Content (first 100 chars): {result['content'][:100]}...")
            print(f"   Distance: {result.get('distance', 'N/A')}")
            
            # Print metadata in a readable format
            metadata = result.get('metadata', {})
            print(f"   Metadata:")
            for key, value in metadata.items():
                print(f"      {key}: {value}")
                
        # Test a specific search for "demand forecasting"
        print("\n" + "=" * 60)
        print("🔍 Testing Search for 'demand forecasting':")
        print("-" * 40)
        
        # First generate embedding for the query
        from app.llm.base import create_llm_provider
        llm_provider = await create_llm_provider()
        query_result = await llm_provider.generate_embedding("demand forecasting")
        
        if query_result.success:
            search_results = await vector_db.search(
                collection_name=collection_name,
                query_embedding=query_result.embedding,
                limit=3
            )
            
            for i, result in enumerate(search_results, 1):
                print(f"\n📄 Result {i} (distance: {result.get('distance', 'N/A'):.3f}):")
                print(f"   Content: {result['content'][:200]}...")
                
                metadata = result.get('metadata', {})
                print(f"   Tab: {metadata.get('source_tab', 'N/A')}")
                print(f"   Tab ID: {metadata.get('source_tab_id', 'N/A')}")
                print(f"   Section: {metadata.get('source_section', 'N/A')}")
                print(f"   Document ID: {metadata.get('source_document_id', 'N/A')}")
                
                # Show what the URL would be
                doc_id = metadata.get('source_document_id')
                tab_id = metadata.get('source_tab_id')
                if doc_id and tab_id:
                    url = f"https://docs.google.com/document/d/{doc_id}/edit?tab={tab_id}"
                    print(f"   Generated URL: {url}")
                else:
                    print(f"   ❌ Missing data for URL generation")
        else:
            print(f"❌ Failed to generate embedding: {query_result.error}")
        
    except Exception as e:
        print(f"❌ Inspection failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(inspect_vector_db())