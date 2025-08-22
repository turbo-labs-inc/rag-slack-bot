"""Microsoft Teams bot message handler."""

import logging
import re
from typing import Any

from app.embedding import DocumentIndexer
from app.query import QueryContext, QueryProcessor

logger = logging.getLogger(__name__)


class TeamsHandler:
    """Handle Microsoft Teams bot messages."""

    def __init__(self):
        """Initialize Teams handler with document processing components."""
        self.indexer = DocumentIndexer()
        self.query_processor = QueryProcessor(indexer=self.indexer)
        logger.info("Teams handler initialized")

    async def process_activity(self, activity: dict[str, Any]) -> dict[str, Any]:
        """
        Process Teams activity and return response.
        
        Args:
            activity: Teams activity payload
            
        Returns:
            Response message for Teams
        """
        activity_type = activity.get("type", "")
        
        # Handle different activity types
        if activity_type == "message":
            return await self._handle_message(activity)
        elif activity_type == "conversationUpdate":
            return await self._handle_conversation_update(activity)
        else:
            logger.info(f"Ignoring activity type: {activity_type}")
            return {"type": "message", "text": ""}

    async def _handle_message(self, activity: dict[str, Any]) -> dict[str, Any]:
        """Handle message activity from Teams."""
        text = activity.get("text", "").strip()
        
        # Remove bot mentions (Teams adds <at>@BotName</at> tags)
        text = re.sub(r'<at>.*?</at>', '', text).strip()
        
        # Extract user info
        from_user = activity.get("from", {})
        user_id = from_user.get("id", "unknown")
        user_name = from_user.get("name", "User")
        
        # Extract channel/conversation info
        conversation = activity.get("conversation", {})
        channel_id = conversation.get("id", "unknown")
        
        logger.info(f"Teams user {user_name} ({user_id}) asked: {text}")
        
        # Parse command
        if text.startswith("/ask "):
            question = text[5:].strip()
        elif text.startswith("/help"):
            return self._get_help_response()
        elif text.startswith("/update"):
            return {"type": "message", "text": "🔄 Document update feature coming soon!"}
        elif text.startswith("/sources"):
            return {"type": "message", "text": "📚 Available sources: Google Docs documents"}
        elif text.startswith("/feedback"):
            return {"type": "message", "text": "💭 Please send feedback to your administrator"}
        else:
            # Treat as a question if no command prefix
            question = text
        
        if not question:
            return {"type": "message", "text": "Please ask a question. Type `/help` for assistance."}
        
        try:
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
                return {
                    "type": "message",
                    "text": "❌ I couldn't find any relevant information for your question. Try rephrasing or ask about a different topic."
                }
            
            # Format response for Teams (using markdown)
            response_text = f"**Answer:** {result.answer}\n\n"
            
            if result.search_results:
                response_text += "**📚 Sources:**\n\n"
                
                # Track unique documents
                seen_docs = {}
                for source in result.search_results[:5]:
                    doc_name = source.source_tab or "Document"
                    # Clean up document name
                    if doc_name.endswith('.docx'):
                        doc_name = doc_name[:-5]
                    elif doc_name.endswith('.doc'):
                        doc_name = doc_name[:-4]
                    
                    if doc_name not in seen_docs:
                        seen_docs[doc_name] = {
                            'url': source.document_url,
                            'sections': [],
                            'similarity': source.similarity
                        }
                    
                    section = source.source_section
                    if section and section not in seen_docs[doc_name]['sections']:
                        seen_docs[doc_name]['sections'].append(section)
                    
                    # Track best similarity
                    if source.similarity > seen_docs[doc_name]['similarity']:
                        seen_docs[doc_name]['similarity'] = source.similarity
                
                # Sort and format
                sorted_docs = sorted(seen_docs.items(), key=lambda x: x[1]['similarity'], reverse=True)
                
                for doc_name, doc_info in sorted_docs[:4]:
                    confidence = f"({doc_info['similarity']:.0%})"
                    
                    # Create hyperlink if URL exists
                    if doc_info['url']:
                        doc_display = f"[{doc_name}]({doc_info['url']})"
                    else:
                        doc_display = doc_name
                    
                    # Format with sections
                    if doc_info['sections']:
                        sections_text = ", ".join(doc_info['sections'][:2])
                        if len(doc_info['sections']) > 2:
                            sections_text += f" +{len(doc_info['sections']) - 2} more"
                        response_text += f"• {doc_display} {confidence} → _{sections_text}_\n"
                    else:
                        response_text += f"• {doc_display} {confidence}\n"
            
            return {"type": "message", "text": response_text}
            
        except Exception as e:
            logger.error(f"Error processing Teams query: {e}", exc_info=True)
            return {
                "type": "message",
                "text": f"❌ Sorry, I encountered an error: {str(e)}"
            }

    async def _handle_conversation_update(self, activity: dict[str, Any]) -> dict[str, Any]:
        """Handle conversation update events (bot added to team/chat)."""
        members_added = activity.get("membersAdded", [])
        bot_id = activity.get("recipient", {}).get("id")
        
        # Check if bot was added
        for member in members_added:
            if member.get("id") == bot_id:
                return {
                    "type": "message",
                    "text": (
                        "👋 Hello! I'm Captain Spire, your document Q&A assistant.\n\n"
                        "I can help you find information from your organization's documentation.\n\n"
                        "**Available commands:**\n"
                        "• `/ask [question]` - Ask a question about documentation\n"
                        "• `/help` - Show this help message\n"
                        "• `/sources` - List available document sources\n"
                        "• `/feedback` - Provide feedback\n\n"
                        "You can also just type your question directly!"
                    )
                }
        
        return {"type": "message", "text": ""}

    def _get_help_response(self) -> dict[str, Any]:
        """Get help message response."""
        return {
            "type": "message",
            "text": (
                "**Captain Spire - Document Q&A Assistant**\n\n"
                "I can help you find information from your organization's documentation.\n\n"
                "**How to use:**\n"
                "• Type `/ask [your question]` or just type your question directly\n"
                "• I'll search through available documents and provide relevant answers\n\n"
                "**Commands:**\n"
                "• `/ask [question]` - Ask a question\n"
                "• `/help` - Show this help message\n"
                "• `/sources` - List available sources\n"
                "• `/feedback` - Provide feedback\n\n"
                "**Examples:**\n"
                "• `/ask What is the onboarding process?`\n"
                "• `/ask How do I request time off?`\n"
                "• `What are the coding standards?` (direct question)"
            )
        }