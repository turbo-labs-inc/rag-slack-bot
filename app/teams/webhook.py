"""Teams Incoming Webhook integration."""

import logging
from typing import Any

import aiohttp

from app.embedding import DocumentIndexer
from app.query import QueryContext, QueryProcessor

logger = logging.getLogger(__name__)


class TeamsWebhookHandler:
    """Handle Teams interactions via Incoming Webhooks."""

    def __init__(self, webhook_url: str | None = None):
        """Initialize webhook handler."""
        self.webhook_url = webhook_url
        self.indexer = DocumentIndexer()
        self.query_processor = QueryProcessor(indexer=self.indexer)
        logger.info("Teams webhook handler initialized")

    async def send_to_teams(self, message: dict[str, Any]) -> bool:
        """
        Send a message to Teams via webhook.
        
        Args:
            message: Adaptive Card or simple message dict
            
        Returns:
            True if successful
        """
        if not self.webhook_url:
            logger.error("No Teams webhook URL configured")
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=message) as response:
                    if response.status == 200:
                        logger.info("Message sent to Teams successfully")
                        return True
                    else:
                        logger.error(f"Failed to send to Teams: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error sending to Teams: {e}")
            return False

    async def process_question(self, question: str, user_name: str = "User") -> dict[str, Any]:
        """
        Process a question and format response for Teams.
        
        Args:
            question: The user's question
            user_name: Name of the user asking
            
        Returns:
            Adaptive Card message for Teams
        """
        logger.info(f"Processing question from {user_name}: {question}")
        
        try:
            # Create query context
            context = QueryContext(
                user_id=user_name,
                channel_id="teams-webhook",
            )
            
            # Process query
            result = await self.query_processor.process_query(
                query=question,
                context=context,
                search_limit=5,
                min_similarity=0.1,
            )
            
            # Format as Adaptive Card for rich formatting
            if not result.search_results:
                return self._create_simple_message(
                    "❌ I couldn't find relevant information for your question. Try rephrasing or ask about a different topic."
                )
            
            # Create sections for the card
            sections = [
                {
                    "activityTitle": f"Question from {user_name}",
                    "activitySubtitle": question,
                    "text": result.answer,
                    "facts": []
                }
            ]
            
            # Add sources as facts
            for i, source in enumerate(result.search_results[:3], 1):
                source_name = source.source_tab or "Document"
                confidence = f"{source.similarity:.0%}"
                sections[0]["facts"].append({
                    "name": f"Source {i}",
                    "value": f"{source_name} ({confidence})"
                })
            
            return {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "themeColor": "0078D4",
                "summary": f"Answer to: {question[:50]}...",
                "sections": sections
            }
            
        except Exception as e:
            logger.error(f"Error processing question: {e}", exc_info=True)
            return self._create_simple_message(f"❌ Error: {str(e)}")

    def _create_simple_message(self, text: str) -> dict[str, Any]:
        """Create a simple text message for Teams."""
        return {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "text": text
        }

    async def send_answer(self, question: str, user_name: str = "User") -> bool:
        """
        Process a question and send the answer to Teams.
        
        Args:
            question: The user's question
            user_name: Name of the user
            
        Returns:
            True if successful
        """
        message = await self.process_question(question, user_name)
        return await self.send_to_teams(message)