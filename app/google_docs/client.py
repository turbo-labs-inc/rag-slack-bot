"""Google Docs client for reading and parsing documents."""

import json
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import get_settings


class GoogleDocsClient:
    """Client for interacting with Google Docs API."""

    def __init__(self, service_account_path: Path | None = None):
        """Initialize the Google Docs client.

        Args:
            service_account_path: Path to service account credentials JSON file
        """
        if service_account_path:
            self.service_account_path = service_account_path
        else:
            settings = get_settings()
            self.service_account_path = settings.google_service_account_key_path
        self.scopes = [
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        self._service = None

    def _get_credentials(self) -> service_account.Credentials:
        """Get service account credentials."""
        if not self.service_account_path.exists():
            raise FileNotFoundError(
                f"Service account credentials not found at: {self.service_account_path}"
            )

        credentials = service_account.Credentials.from_service_account_file(
            str(self.service_account_path), scopes=self.scopes
        )
        return credentials

    def _get_service(self):
        """Get Google Docs service instance."""
        if self._service is None:
            credentials = self._get_credentials()
            self._service = build("docs", "v1", credentials=credentials)
        return self._service

    def get_document(self, document_id: str, include_tabs: bool = True) -> dict[str, Any]:
        """Get a Google Docs document.

        Args:
            document_id: The ID of the Google Docs document
            include_tabs: Whether to include tab content in the response

        Returns:
            Document data from Google Docs API

        Raises:
            Exception: If document cannot be accessed
        """
        try:
            service = self._get_service()

            # Build the request with optional tab inclusion
            request = service.documents().get(documentId=document_id)

            # Include tabs content if requested
            if include_tabs:
                try:
                    # Use the includeTabsContent parameter to get all tabs
                    print("🔍 Requesting document with all tabs content...")
                    document = (
                        service.documents()
                        .get(documentId=document_id, includeTabsContent=True)
                        .execute()
                    )

                    if "tabs" in document and len(document["tabs"]) > 0:
                        print(f"✅ Successfully retrieved {len(document['tabs'])} tabs")
                    else:
                        print("⚠️  No tabs found in response, document may be single-tab")

                except Exception as tab_error:
                    print(f"⚠️  Error requesting tabs content: {tab_error}")
                    print("🔄 Falling back to basic request...")
                    # Fall back to basic request
                    document = service.documents().get(documentId=document_id).execute()
            else:
                document = request.execute()

            return document
        except Exception as e:
            raise Exception(f"Failed to get document {document_id}: {str(e)}")

    def get_document_title(self, document_id: str) -> str:
        """Get the title of a Google Docs document.

        Args:
            document_id: The ID of the Google Docs document

        Returns:
            Document title
        """
        document = self.get_document(document_id)
        return document.get("title", "Untitled")

    def extract_document_id_from_url(self, url: str) -> str:
        """Extract document ID from a Google Docs URL.

        Args:
            url: Google Docs URL

        Returns:
            Document ID

        Raises:
            ValueError: If URL format is invalid
        """
        # Handle various Google Docs URL formats
        if "/document/d/" in url:
            # Format: https://docs.google.com/document/d/DOC_ID/edit
            parts = url.split("/document/d/")
            if len(parts) >= 2:
                doc_id = parts[1].split("/")[0]
                return doc_id

        # If it's already just the ID
        if len(url) == 44 and url.replace("-", "").replace("_", "").isalnum():
            return url

        raise ValueError(f"Invalid Google Docs URL format: {url}")

    def health_check(self) -> bool:
        """Check if the client can access Google Docs API.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            credentials = self._get_credentials()
            # Just check if we can build the service
            service = build("docs", "v1", credentials=credentials)
            return True
        except Exception:
            return False
