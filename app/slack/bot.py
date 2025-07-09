"""Slack bot implementation using Slack Bolt framework."""

import asyncio
import logging
from typing import Any

from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.context.ack.async_ack import AsyncAck
from slack_bolt.context.respond.async_respond import AsyncRespond
from slack_bolt.context.say.async_say import AsyncSay
from slack_bolt.request.async_request import AsyncBoltRequest

from app.config import get_settings
from app.embedding import DocumentIndexer
from app.google_docs import GoogleDocsClient, GoogleDocsParser
from app.query import QueryProcessor, QueryContext

logger = logging.getLogger(__name__)


class GravitateTutorBot:
    """Gravitate Tutor Slack bot for document Q&A."""

    def __init__(self):
        """Initialize the Slack bot."""
        self.settings = get_settings()
        
        # Initialize Slack app
        self.app = AsyncApp(token=self.settings.slack_bot_token)
        
        # Initialize document components
        self.indexer = DocumentIndexer()
        self.query_processor = QueryProcessor(indexer=self.indexer)
        self.docs_client = None
        self.docs_parser = None
        
        # Register event handlers
        self._register_handlers()
        
        logger.info("Gravitate Tutor bot initialized")

    def _register_handlers(self):
        """Register Slack event handlers."""
        
        # Slash commands
        self.app.command("/gt_ask")(self._handle_ask_command)
        self.app.command("/gt_update")(self._handle_update_command)
        self.app.command("/gt_help")(self._handle_help_command)
        
        # App mentions
        self.app.event("app_mention")(self._handle_app_mention)
        
        # Direct messages
        self.app.event("message")(self._handle_direct_message)

    async def _handle_ask_command(
        self,
        ack: AsyncAck,
        command: dict[str, Any],
        respond: AsyncRespond,
    ):
        """Handle /gt_ask slash command."""
        await ack()
        
        question = command.get("text", "").strip()
        if not question:
            await respond("Please provide a question. Usage: `/gt_ask [your question]`")
            return
        
        user_id = command["user_id"]
        channel_id = command.get("channel_id")
        logger.info(f"User {user_id} asked: {question}")
        
        try:
            # Show typing indicator
            await respond("🤔 Searching documentation...")
            
            # Create query context
            context = QueryContext(
                user_id=user_id,
                channel_id=channel_id,
            )
            
            # Process query with RAG pipeline
            result = await self.query_processor.process_query(
                query=question,
                context=context,
                search_limit=5,
                min_similarity=0.1,
            )
            
            if not result.search_results:
                await respond("❌ I couldn't find any relevant information for your question. Try rephrasing or ask about a different topic.")
                return
            
            # Format response for Slack
            response = self.query_processor.format_for_slack(result)
            await respond(response)
            
        except Exception as e:
            logger.error(f"Error handling ask command: {e}")
            await respond("❌ Sorry, I encountered an error while searching. Please try again later.")

    async def _handle_update_command(
        self,
        ack: AsyncAck,
        command: dict[str, Any],
        respond: AsyncRespond,
    ):
        """Handle /gt_update slash command."""
        await ack()
        
        user_id = command["user_id"]
        logger.info(f"User {user_id} requested document update")
        
        try:
            await respond("🔄 Starting document re-indexing... This may take a few minutes.")
            
            # Initialize Google Docs components if needed
            if not self.docs_client:
                self.docs_client = GoogleDocsClient(
                    service_account_path=self.settings.google_service_account_key_path
                )
                self.docs_parser = GoogleDocsParser()
            
            # Fetch and parse document
            document = self.docs_client.get_document(self.settings.google_docs_id)
            parsed_doc = self.docs_parser.parse_document(document)
            
            # Re-index document
            stats = await self.indexer.index_document(
                document=parsed_doc,
                collection_name="document_chunks",
                use_smart_chunking=True,
                generate_embeddings=True,
                batch_size=10
            )
            
            response = (
                "✅ Document re-indexing completed!\n"
                f"• Document: {stats['document_title']}\n"
                f"• Chunks created: {stats['chunks_created']}\n"
                f"• Chunks with embeddings: {stats['chunks_with_embeddings']}\n"
                f"• Chunks stored: {stats['chunks_stored']}"
            )
            
            await respond(response)
            
        except Exception as e:
            logger.error(f"Error handling update command: {e}")
            await respond("❌ Failed to update documentation. Please check the logs and try again.")

    async def _handle_help_command(
        self,
        ack: AsyncAck,
        command: dict[str, Any],
        respond: AsyncRespond,
    ):
        """Handle /gt_help slash command."""
        await ack()
        
        help_text = (
            "🤖 *Gravitate Tutor Bot* - Documentation Q&A Assistant\n\n"
            "*Available Commands:*\n"
            "• `/gt_ask [question]` - Ask a question about the documentation\n"
            "• `/gt_update` - Re-index the documentation (admin only)\n"
            "• `/gt_help` - Show this help message\n\n"
            "*Examples:*\n"
            "• `/gt_ask What is supply and dispatch?`\n"
            "• `/gt_ask How does pricing work?`\n"
            "• `/gt_ask Features of fuel delivery`\n\n"
            "*Tips:*\n"
            "• Be specific in your questions for better results\n"
            "• You can also mention me directly: @gravitate-tutor\n"
            "• I search through the latest documentation to provide accurate answers"
        )
        
        await respond(help_text)

    async def _handle_app_mention(
        self,
        event: dict[str, Any],
        say: AsyncSay,
    ):
        """Handle app mentions."""
        text = event.get("text", "")
        user = event.get("user")
        channel = event.get("channel")
        
        # Remove the bot mention from the text
        question = text.split(">", 1)[-1].strip()
        
        if not question:
            await say("Hi! Ask me a question about the documentation. Use `/gt_help` for more info.")
            return
        
        logger.info(f"User {user} mentioned bot with: {question}")
        
        try:
            # Create query context
            context = QueryContext(
                user_id=user,
                channel_id=channel,
            )
            
            # Process query with RAG pipeline
            result = await self.query_processor.process_query(
                query=question,
                context=context,
                search_limit=5,
                min_similarity=0.1,
            )
            
            if not result.search_results:
                await say("❌ I couldn't find relevant information. Try rephrasing your question or use `/gt_help` for examples.")
                return
            
            # Format and send response
            response = self.query_processor.format_for_slack(result)
            await say(response)
            
        except Exception as e:
            logger.error(f"Error handling app mention: {e}")
            await say("❌ Sorry, I encountered an error. Please try again later.")

    async def _handle_direct_message(
        self,
        event: dict[str, Any],
        say: AsyncSay,
    ):
        """Handle direct messages."""
        # Skip messages from bots
        if event.get("bot_id"):
            return
        
        # Skip if message is not in DM channel
        channel_type = event.get("channel_type")
        if channel_type != "im":
            return
        
        text = event.get("text", "").strip()
        user = event.get("user")
        
        if not text:
            return
        
        logger.info(f"User {user} sent DM: {text}")
        
        # Handle help requests
        if text.lower() in ["help", "?", "/help"]:
            help_text = (
                "🤖 *Gravitate Tutor Bot*\n\n"
                "Just ask me any question about the documentation!\n\n"
                "*Examples:*\n"
                "• What is supply and dispatch?\n"
                "• How does pricing work?\n"
                "• Features of fuel delivery\n\n"
                "Use `/gt_help` in channels for full command list."
            )
            await say(help_text)
            return
        
        try:
            # Create query context
            context = QueryContext(
                user_id=user,
                channel_id=event.get("channel"),
            )
            
            # Process query with RAG pipeline
            result = await self.query_processor.process_query(
                query=text,
                context=context,
                search_limit=5,
                min_similarity=0.1,
            )
            
            if not result.search_results:
                await say("❌ I couldn't find relevant information. Try rephrasing your question.")
                return
            
            # Format and send response
            response = self.query_processor.format_for_slack(result)
            await say(response)
            
        except Exception as e:
            logger.error(f"Error handling direct message: {e}")
            await say("❌ Sorry, I encountered an error. Please try again later.")


    async def start(self):
        """Start the Slack bot."""
        logger.info("Starting Gravitate Tutor bot...")
        
        # Initialize and health check components
        health = await self.query_processor.health_check()
        if not health["overall"]:
            logger.error("Health check failed - bot may not work properly")
            logger.error(f"Health status: {health}")
        
        # Start Socket Mode handler
        handler = AsyncSocketModeHandler(self.app, self.settings.slack_app_token)
        await handler.start_async()

    async def stop(self):
        """Stop the Slack bot."""
        logger.info("Stopping Gravitate Tutor bot...")
        # The Socket Mode handler will handle cleanup