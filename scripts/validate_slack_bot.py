"""Validation script for Slack bot integration."""

import asyncio
import logging
from pathlib import Path

from app.config import get_settings
from app.slack import GravitateTutorBot

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_slack_bot():
    """Test Slack bot initialization and health checks."""
    print("🤖 Testing Slack Bot Integration")
    print("=" * 50)
    
    try:
        # Load settings
        settings = get_settings()
        print(f"📋 Slack Bot Token: {settings.slack_bot_token[:20]}...")
        print(f"📋 Slack App Token: {settings.slack_app_token[:20]}...")
        print()
        
        # Initialize bot
        print("🚀 Initializing Gravitate Tutor bot...")
        bot = GravitateTutorBot()
        print("✅ Bot initialized successfully")
        print()
        
        # Test health checks
        print("🔍 Performing health checks...")
        health = await bot.indexer.health_check()
        print(f"   Vector Database: {'✅' if health['vector_database'] else '❌'}")
        print(f"   LLM Provider: {'✅' if health['llm_provider'] else '❌'}")
        print(f"   Overall: {'✅' if health['overall'] else '❌'}")
        print()
        
        # Check if we have indexed data
        try:
            stats = await bot.indexer.get_indexing_stats("document_chunks")
            print("📊 Document Index Status:")
            print(f"   Collection: {stats.get('name', 'N/A')}")
            print(f"   Total chunks: {stats.get('total_chunks', 0)}")
            print(f"   Unique sections: {stats.get('unique_sections', 'N/A')}")
            print()
            
            if stats.get('total_chunks', 0) > 0:
                print("✅ Document index is ready for queries")
            else:
                print("⚠️  No documents indexed yet - run indexing first")
                print("   Use /gt_update command or run validation scripts")
        except Exception as e:
            print(f"⚠️  Could not check document index: {e}")
            print("   This is expected if no documents have been indexed yet")
        print()
        
        # Test search functionality with synthetic query
        if health['overall']:
            print("🔍 Testing search functionality...")
            try:
                # Try a simple search to test the pipeline
                results = await bot.indexer.search_documents(
                    query="test query",
                    collection_name="document_chunks",
                    limit=3
                )
                print(f"✅ Search completed - found {len(results)} results")
            except Exception as e:
                print(f"⚠️  Search test failed: {e}")
                print("   This is expected if no documents have been indexed yet")
        print()
        
        print("🎉 Slack bot validation completed!")
        print()
        print("💡 Next steps:")
        print("   1. Make sure ChromaDB is running: scripts/dev_chroma.sh start")
        print("   2. Index documents: PYTHONPATH=. uv run scripts/validate_vector_database.py")
        print("   3. Start the bot: PYTHONPATH=. uv run app/main.py")
        print("   4. Test commands in Slack:")
        print("      - /gt_help")
        print("      - /gt_ask What is supply and dispatch?")
        print("      - @gravitate-tutor [question]")
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_slack_bot())