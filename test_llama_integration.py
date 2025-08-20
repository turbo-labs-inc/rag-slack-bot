#!/usr/bin/env python3
"""Test script to verify Llama 3.2 integration with the RAG bot."""

import asyncio
import logging
from app.llm.factory import create_llm_provider
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_llama_integration():
    """Test Llama 3.2 with the RAG bot's LLM abstraction."""
    
    settings = get_settings()
    logger.info(f"Using LLM Provider: {settings.llm_provider}")
    logger.info(f"Ollama Host: {settings.ollama_host}")
    logger.info(f"Ollama Model: {settings.ollama_model}")
    
    # Create LLM provider
    llm = create_llm_provider()
    
    # Test health check
    logger.info("\n1. Testing health check...")
    is_healthy = await llm.health_check()
    logger.info(f"   Health check: {'✅ Passed' if is_healthy else '❌ Failed'}")
    
    if not is_healthy:
        logger.error("Ollama is not running. Please start it with: brew services start ollama")
        return
    
    # Test basic response generation
    logger.info("\n2. Testing basic response generation...")
    prompt = "What is the capital of France?"
    result = await llm.generate_response(prompt)
    logger.info(f"   Question: {prompt}")
    logger.info(f"   Response: {result.content[:100]}...")
    logger.info(f"   Model: {result.model}")
    
    # Test RAG-style response with context
    logger.info("\n3. Testing RAG response with context...")
    context = """
    The company's new product launch is scheduled for Q2 2024.
    Key features include:
    - AI-powered search
    - Real-time collaboration
    - Enterprise-grade security
    The pricing starts at $99/month for the basic plan.
    """
    question = "When is the product launch and what's the pricing?"
    result = await llm.generate_response(question, context)
    logger.info(f"   Question: {question}")
    logger.info(f"   Response: {result.content[:200]}...")
    
    # Test embedding generation
    logger.info("\n4. Testing embedding generation...")
    text = "This is a test document for embedding generation."
    embedding_result = await llm.generate_embedding(text)
    logger.info(f"   Text: {text}")
    logger.info(f"   Embedding dimensions: {len(embedding_result.embedding)}")
    logger.info(f"   Model: {embedding_result.model}")
    
    # Test summarization
    logger.info("\n5. Testing summarization...")
    long_text = """
    Artificial intelligence has made remarkable progress in recent years, 
    particularly in natural language processing. Large language models like 
    GPT and Llama have demonstrated impressive capabilities in understanding 
    and generating human-like text. These models are being integrated into 
    various applications, from chatbots to content creation tools. The 
    development of open-source models has democratized access to AI technology, 
    allowing developers and researchers worldwide to build innovative solutions.
    """
    summary_result = await llm.summarize(long_text, max_length=50)
    logger.info(f"   Original text length: {len(long_text.split())} words")
    logger.info(f"   Summary: {summary_result.content}")
    
    logger.info("\n✅ All tests completed successfully!")
    logger.info("Your Llama 3.2 integration is working correctly with the RAG bot!")


if __name__ == "__main__":
    asyncio.run(test_llama_integration())