"""Test script to validate Gemini configuration."""

import asyncio
import logging
from app.config import get_settings
from app.llm.factory import create_llm_provider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_gemini_config():
    """Test Gemini provider configuration."""
    print("🔍 Testing Gemini Configuration")
    print("=" * 50)
    
    try:
        # Load settings
        settings = get_settings()
        print(f"📋 LLM Provider: {settings.llm_provider}")
        print(f"📋 Gemini Model: {settings.gemini_model}")
        print(f"📋 Gemini API Key: {settings.gemini_api_key[:20]}...")
        print()
        
        # Create LLM provider
        print("🚀 Creating Gemini provider...")
        llm_provider = create_llm_provider()
        print("✅ Gemini provider created successfully")
        print(f"   Provider type: {type(llm_provider).__name__}")
        print()
        
        # Test a simple response
        print("🤖 Testing response generation...")
        response = await llm_provider.generate_response(
            prompt="What is artificial intelligence? Answer in one sentence."
        )
        
        if response.success:
            print("✅ Response generation successful")
            print(f"   Response: {response.response[:100]}...")
            print(f"   Token count: {response.token_count}")
        else:
            print(f"❌ Response failed: {response.error}")
        print()
        
        # Test embeddings
        print("🔢 Testing embedding generation...")
        embedding = await llm_provider.generate_embedding("test embedding text")
        
        if embedding.success:
            print("✅ Embedding generation successful")
            print(f"   Embedding dimensions: {len(embedding.embedding)}")
            print(f"   Model: {embedding.model}")
        else:
            print(f"❌ Embedding failed: {embedding.error}")
        
        print("\n🎉 Gemini configuration test completed!")
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_gemini_config())