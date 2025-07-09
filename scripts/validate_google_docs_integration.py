"""Test script for Google Docs integration."""

import asyncio
from pathlib import Path

from app.google_docs import GoogleDocsClient, GoogleDocsParser


async def test_google_docs_integration():
    """Test Google Docs client and parser."""
    # Extract document ID from the URL
    url = "https://docs.google.com/document/d/1zbZjXJP948_Ud6vNYGZ5-Kae9q456SHgRiSEtEX-J9M/edit?tab=t.pbxyea5hgyv7#heading=h.ua4i2dyops6a"

    # Create client with explicit path to avoid settings validation
    credentials_path = Path("credentials/google-docs-service-account.json")
    client = GoogleDocsClient(service_account_path=credentials_path)
    parser = GoogleDocsParser()

    try:
        # Extract document ID
        document_id = client.extract_document_id_from_url(url)
        print(f"Document ID: {document_id}")

        # Test health check
        print("Testing health check...")
        health_ok = client.health_check()
        print(f"Health check: {'✓' if health_ok else '✗'}")

        if not health_ok:
            print("Health check failed - cannot continue")
            return

        # Get document
        print("Fetching document...")
        document = client.get_document(document_id)
        print(f"Document title: {document.get('title', 'Unknown')}")

        # First, let's examine the raw document structure
        print("Raw document structure (first 3 elements):")
        content = document.get("body", {}).get("content", [])
        for i, item in enumerate(content[:3]):
            print(f"Item {i + 1}: {item}")

        # Parse document
        print("\nParsing document...")
        parsed_doc = parser.parse_document(document)
        print(f"Parsed document: {parsed_doc.title}")
        print(f"Number of sections: {len(parsed_doc.sections)}")

        # Display section structure
        for i, section in enumerate(parsed_doc.sections):
            print(f"\nSection {i + 1}: '{section.title}' (Level {section.level})")
            print(f"  Elements: {len(section.elements)}")
            print(f"  Subsections: {len(section.subsections)}")

            # Show first few elements with their types
            for j, element in enumerate(section.elements[:5]):
                text_preview = (
                    element.text[:100] + "..." if len(element.text) > 100 else element.text
                )
                print(
                    f"    Element {j + 1} ({element.type}, level {element.level}): {text_preview}"
                )

        # Show full text preview
        full_text = parsed_doc.get_full_text()
        print(f"\nFull text length: {len(full_text)} characters")
        print(f"First 500 characters:\n{full_text[:500]}...")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_google_docs_integration())
