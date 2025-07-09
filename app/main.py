"""Main entry point for the Document Q&A Slack Bot."""

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.config import get_settings
from app.slack import GravitateTutorBot

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Configure logging (use INFO as default until settings are loaded)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main application entry point."""
    settings = get_settings()
    logger.info(f"Starting Document Q&A Slack Bot in {settings.environment} mode")
    logger.info(f"Using LLM provider: {settings.llm_provider}")

    # Validate configuration
    try:
        settings.validate_provider_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Initialize and start Slack bot
    logger.info("Initializing Gravitate Tutor bot...")
    bot = GravitateTutorBot()
    
    try:
        logger.info("Starting Slack bot...")
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
