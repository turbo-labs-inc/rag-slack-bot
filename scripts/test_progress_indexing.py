"""Test script to see the enhanced progress tracking in action."""

import asyncio
import logging

from app.config import get_settings
from app.google_docs import GoogleDocsClient, GoogleDocsParser
from app.embedding import DocumentIndexer

# Set up logging - silence httpx spam but keep our logs
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def test_progress_indexing():
    """Test indexing with enhanced progress tracking."""
    print("🧪 Testing Enhanced Progress Tracking")
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
        print(f"📑 Parsed document: {parsed_doc.title}")
        print(f"📊 Found {len(parsed_doc.sections)} sections")
        print()
        
        # Index with progress tracking
        # Using small batch size to see more progress updates
        stats = await indexer.index_document(
            document=parsed_doc,
            collection_name="progress_test_chunks",
            use_smart_chunking=False,  # Use basic for faster testing
            generate_embeddings=True,
            batch_size=3,  # Small batches to see more progress
        )
        
        print("\n🎯 Final Results:")
        print(f"   Document: {stats['document_title']}")
        print(f"   Collection: {stats['collection_name']}")
        print(f"   Chunks: {stats['chunks_created']}")
        print(f"   Embeddings: {stats['chunks_with_embeddings']}")
        print(f"   Stored: {stats['chunks_stored']}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_progress_indexing())