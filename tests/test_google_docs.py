"""Tests for Google Docs integration."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.google_docs import DocumentElement, DocumentSection, GoogleDocsClient, GoogleDocsParser


class TestGoogleDocsClient:
    """Test Google Docs client."""

    def test_extract_document_id_from_url(self):
        """Test extracting document ID from various URL formats."""
        client = GoogleDocsClient(service_account_path=Path("/fake/path"))

        # Standard Google Docs URL
        url1 = (
            "https://docs.google.com/document/d/1zbZjXJP948_Ud6vNYGZ5-Kae9q456SHgRiSEtEX-J9M/edit"
        )
        assert (
            client.extract_document_id_from_url(url1)
            == "1zbZjXJP948_Ud6vNYGZ5-Kae9q456SHgRiSEtEX-J9M"
        )

        # URL with additional parameters
        url2 = "https://docs.google.com/document/d/1zbZjXJP948_Ud6vNYGZ5-Kae9q456SHgRiSEtEX-J9M/edit?tab=t.pbxyea5hgyv7#heading=h.ua4i2dyops6a"
        assert (
            client.extract_document_id_from_url(url2)
            == "1zbZjXJP948_Ud6vNYGZ5-Kae9q456SHgRiSEtEX-J9M"
        )

        # Just the document ID
        doc_id = "1zbZjXJP948_Ud6vNYGZ5-Kae9q456SHgRiSEtEX-J9M"
        assert client.extract_document_id_from_url(doc_id) == doc_id

    def test_extract_document_id_invalid_url(self):
        """Test extracting document ID from invalid URL."""
        client = GoogleDocsClient(service_account_path=Path("/fake/path"))

        with pytest.raises(ValueError, match="Invalid Google Docs URL format"):
            client.extract_document_id_from_url("https://example.com/invalid")

    def test_health_check_success(self):
        """Test successful health check."""
        client = GoogleDocsClient(service_account_path=Path("/fake/path"))

        with patch.object(client, "_get_credentials"):
            with patch("app.google_docs.client.build") as mock_build:
                mock_build.return_value = MagicMock()
                assert client.health_check() is True

    def test_health_check_failure(self):
        """Test failed health check."""
        client = GoogleDocsClient(service_account_path=Path("/fake/path"))

        with patch.object(client, "_get_credentials", side_effect=Exception("Auth failed")):
            assert client.health_check() is False


class TestGoogleDocsParser:
    """Test Google Docs parser."""

    def test_parse_simple_document(self):
        """Test parsing a simple document."""
        parser = GoogleDocsParser()

        # Mock document data
        document_data = {
            "title": "Test Document",
            "documentId": "test-doc-id",
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {
                                    "textRun": {
                                        "content": "What is this document about?\n",
                                        "textStyle": {
                                            "backgroundColor": {
                                                "color": {"rgbColor": {"red": 1, "green": 1}}
                                            }
                                        },
                                    }
                                }
                            ],
                            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        }
                    },
                    {
                        "paragraph": {
                            "elements": [
                                {
                                    "textRun": {
                                        "content": "This is a test document for parsing.\n",
                                        "textStyle": {},
                                    }
                                }
                            ],
                            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        }
                    },
                ]
            },
        }

        parsed_doc = parser.parse_document(document_data)

        assert parsed_doc.title == "Test Document"
        assert parsed_doc.document_id == "test-doc-id"
        assert len(parsed_doc.sections) == 1

        section = parsed_doc.sections[0]
        assert section.title == "What is this document about?"
        assert section.level == 3
        assert len(section.elements) == 1
        assert section.elements[0].text == "This is a test document for parsing."

    def test_parse_heading_styles(self):
        """Test parsing different heading styles."""
        parser = GoogleDocsParser()

        # Test HEADING_1 style
        paragraph_data = {
            "elements": [{"textRun": {"content": "Heading 1\n", "textStyle": {}}}],
            "paragraphStyle": {"namedStyleType": "HEADING_1"},
        }

        element = parser._parse_paragraph(paragraph_data)
        assert element.type == "heading"
        assert element.level == 1
        assert element.text == "Heading 1"

        # Test TITLE style
        paragraph_data = {
            "elements": [{"textRun": {"content": "Document Title\n", "textStyle": {}}}],
            "paragraphStyle": {"namedStyleType": "TITLE"},
        }

        element = parser._parse_paragraph(paragraph_data)
        assert element.type == "heading"
        assert element.level == 1
        assert element.text == "Document Title"

    def test_parse_question_as_heading(self):
        """Test parsing highlighted questions as headings."""
        parser = GoogleDocsParser()

        paragraph_data = {
            "elements": [
                {
                    "textRun": {
                        "content": "What is the question?\n",
                        "textStyle": {
                            "backgroundColor": {"color": {"rgbColor": {"red": 1, "green": 1}}}
                        },
                    }
                }
            ],
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
        }

        element = parser._parse_paragraph(paragraph_data)
        assert element.type == "heading"
        assert element.level == 3
        assert element.text == "What is the question?"

    def test_parse_regular_paragraph(self):
        """Test parsing regular paragraphs."""
        parser = GoogleDocsParser()

        paragraph_data = {
            "elements": [
                {"textRun": {"content": "This is a regular paragraph.\n", "textStyle": {}}}
            ],
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
        }

        element = parser._parse_paragraph(paragraph_data)
        assert element.type == "paragraph"
        assert element.level == 0
        assert element.text == "This is a regular paragraph."


class TestDocumentModels:
    """Test document data models."""

    def test_document_element(self):
        """Test DocumentElement creation."""
        element = DocumentElement(
            type="paragraph", text="Test content", level=0, style={"bold": True}
        )

        assert element.type == "paragraph"
        assert element.text == "Test content"
        assert element.level == 0
        assert element.style == {"bold": True}

    def test_document_section_get_full_text(self):
        """Test getting full text from document section."""
        section = DocumentSection(
            title="Test Section",
            level=1,
            elements=[
                DocumentElement(type="paragraph", text="First paragraph"),
                DocumentElement(type="paragraph", text="Second paragraph"),
            ],
        )

        full_text = section.get_full_text()
        expected = "Test Section\n\nFirst paragraph\n\nSecond paragraph"
        assert full_text == expected

    def test_document_section_with_subsections(self):
        """Test document section with subsections."""
        subsection = DocumentSection(
            title="Subsection",
            level=2,
            elements=[DocumentElement(type="paragraph", text="Subsection content")],
        )

        section = DocumentSection(
            title="Main Section",
            level=1,
            elements=[DocumentElement(type="paragraph", text="Main content")],
            subsections=[subsection],
        )

        full_text = section.get_full_text()
        expected = "Main Section\n\nMain content\n\nSubsection\n\nSubsection content"
        assert full_text == expected
