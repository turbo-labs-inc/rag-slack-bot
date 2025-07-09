"""Main entry point for the Document Q&A Slack Bot."""

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.config import settings

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main application entry point."""
    logger.info(f"Starting Document Q&A Slack Bot in {settings.environment} mode")
    logger.info(f"Using LLM provider: {settings.llm_provider}")

    # Validate configuration
    try:
        settings.validate_provider_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # TODO: Initialize components
    # - Slack bot
    # - ChromaDB client
    # - LLM provider
    # - Start bot

    logger.info("Bot is ready!")

    # Keep the bot running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
