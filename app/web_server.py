"""Web server for handling Teams webhooks alongside Slack bot."""

import asyncio
import logging
import os
from typing import Any

from aiohttp import web

from app.teams import TeamsHandler
from app.teams.webhook import TeamsWebhookHandler

logger = logging.getLogger(__name__)


class WebServer:
    """HTTP server for Teams webhook endpoints."""

    def __init__(self, port: int = 3000):
        """Initialize web server."""
        self.port = port
        self.app = web.Application()
        self.teams_handler = TeamsHandler()
        # Initialize webhook handler (URL from env var)
        webhook_url = os.getenv("TEAMS_WEBHOOK_URL")
        self.webhook_handler = TeamsWebhookHandler(webhook_url)
        self._setup_routes()
        logger.info(f"Web server initialized on port {port}")

    def _setup_routes(self):
        """Set up HTTP routes."""
        self.app.router.add_get("/", self._handle_health)
        self.app.router.add_get("/health", self._handle_health)
        self.app.router.add_post("/api/teams/messages", self._handle_teams_message)
        self.app.router.add_post("/api/teams/webhook", self._handle_webhook_query)
        logger.info("Routes configured: /, /health, /api/teams/messages, /api/teams/webhook")

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({"status": "healthy", "service": "Captain Spire Bot"})

    async def _handle_webhook_query(self, request: web.Request) -> web.Response:
        """
        Handle webhook query requests.
        
        Expects JSON: {"question": "...", "user": "..."}
        Sends response to Teams via webhook.
        """
        try:
            data = await request.json()
            question = data.get("question", "").strip()
            user_name = data.get("user", "User")
            
            if not question:
                return web.json_response(
                    {"error": "No question provided"},
                    status=400
                )
            
            if not self.webhook_handler.webhook_url:
                return web.json_response(
                    {"error": "No Teams webhook URL configured. Set TEAMS_WEBHOOK_URL environment variable."},
                    status=500
                )
            
            # Process and send to Teams
            success = await self.webhook_handler.send_answer(question, user_name)
            
            if success:
                return web.json_response({"status": "sent", "question": question})
            else:
                return web.json_response({"error": "Failed to send to Teams"}, status=500)
                
        except Exception as e:
            logger.error(f"Error handling webhook query: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_teams_message(self, request: web.Request) -> web.Response:
        """
        Handle Teams bot messages.
        
        This endpoint receives messages from Microsoft Teams Bot Framework.
        """
        try:
            # Get request body
            activity = await request.json()
            logger.info(f"Received Teams activity: type={activity.get('type')}")
            
            # Process activity
            response = await self.teams_handler.process_activity(activity)
            
            # Return response to Teams
            return web.json_response(response)
            
        except Exception as e:
            logger.error(f"Error handling Teams message: {e}", exc_info=True)
            return web.json_response(
                {"type": "message", "text": f"Error: {str(e)}"},
                status=200  # Teams expects 200 even for errors
            )

    async def start(self):
        """Start the web server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.port)
        await site.start()
        logger.info(f"Web server started on port {self.port}")
        logger.info(f"Teams webhook endpoint: http://localhost:{self.port}/api/teams/messages")
        return runner

    async def stop(self, runner):
        """Stop the web server."""
        await runner.cleanup()
        logger.info("Web server stopped")