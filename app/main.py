"""Main entry point for the Document Q&A Slack Bot."""

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.config import get_settings
from app.slack import GravitateTutorBot
from app.web_server import WebServer

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Configure logging (use INFO as default)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main application entry point."""
    settings = get_settings()
    logger.info(f"Starting Document Q&A Bot in {settings.environment} mode")
    logger.info(f"Using LLM provider: {settings.llm_provider}")

    # Validate configuration
    try:
        settings.validate_provider_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Initialize web server for Teams
    logger.info("Starting web server for Teams integration...")
    web_server = WebServer(port=3000)
    web_runner = await web_server.start()

    # Initialize and start Slack bot
    logger.info("Initializing Gravitate Tutor bot...")
    bot = GravitateTutorBot()
    
    try:
        logger.info("Starting Slack bot...")
        # Run both services concurrently
        await asyncio.gather(
            bot.start(),
            asyncio.Event().wait()  # Keep web server running
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await bot.stop()
        await web_server.stop(web_runner)


if __name__ == "__main__":
    asyncio.run(main())
