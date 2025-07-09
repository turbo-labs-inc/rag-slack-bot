"""Google Docs integration module."""

from .client import GoogleDocsClient
from .parser import DocumentElement, DocumentSection, GoogleDocsParser, ParsedDocument

__all__ = [
    "GoogleDocsClient",
    "GoogleDocsParser",
    "DocumentElement",
    "DocumentSection",
    "ParsedDocument",
]
