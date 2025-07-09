"""Script to list all headings from the Google Docs document."""

import asyncio
from pathlib import Path

from app.google_docs import GoogleDocsClient, GoogleDocsParser


async def list_document_headings():
    """List all headings from the Google Docs document."""
    # Your document URL
    url = "https://docs.google.com/document/d/1zbZjXJP948_Ud6vNYGZ5-Kae9q456SHgRiSEtEX-J9M/edit?tab=t.pbxyea5hgyv7#heading=h.ua4i2dyops6a"

    # Create client and parser
    credentials_path = Path("credentials/google-docs-service-account.json")
    client = GoogleDocsClient(service_account_path=credentials_path)
    parser = GoogleDocsParser()

    try:
        # Extract document ID and fetch document
        document_id = client.extract_document_id_from_url(url)
        print(f"📄 Document ID: {document_id}")

        document = client.get_document(document_id)
        print(f"📋 Document Title: {document.get('title', 'Unknown')}")

        # Parse document
        parsed_doc = parser.parse_document(document)

        print(f"\n🔍 Found {len(parsed_doc.sections)} sections with headings:")
        print("=" * 60)

        # List all headings
        for i, section in enumerate(parsed_doc.sections, 1):
            # Show section heading
            if section.title:
                indent = "  " * (section.level - 1) if section.level > 0 else ""
                level_marker = "📌" if section.level == 3 else "📍"
                print(f"{level_marker} {indent}Section {i}: {section.title}")
                print(f"   {indent}├─ Level: {section.level}")
                print(f"   {indent}├─ Elements: {len(section.elements)}")
                print(f"   {indent}└─ Subsections: {len(section.subsections)}")

                # Show first bit of content
                if section.elements:
                    first_element = section.elements[0]
                    preview = (
                        first_element.text[:100] + "..."
                        if len(first_element.text) > 100
                        else first_element.text
                    )
                    print(f"   {indent}   Preview: {preview}")

                print()

                # Show subsections recursively
                if section.subsections:
                    for j, subsection in enumerate(section.subsections, 1):
                        sub_indent = "  " * (subsection.level - 1)
                        print(f"   {sub_indent}└─ Subsection {j}: {subsection.title}")
                        print(f"      {sub_indent}   Level: {subsection.level}")
                        print()

        # Show document stats
        print("=" * 60)
        print("📊 Document Statistics:")
        print(f"   • Total sections: {len(parsed_doc.sections)}")

        total_elements = sum(len(section.elements) for section in parsed_doc.sections)
        print(f"   • Total elements: {total_elements}")

        full_text = parsed_doc.get_full_text()
        print(f"   • Total characters: {len(full_text)}")
        print(f"   • Estimated words: {len(full_text.split())}")

        # Show heading hierarchy
        print(f"\n🏗️  Heading Hierarchy:")
        for i, section in enumerate(parsed_doc.sections, 1):
            if section.title:
                level_prefix = "  " * (section.level - 1) if section.level > 0 else ""
                print(f"{level_prefix}├─ (Level {section.level}) {section.title}")

                for j, subsection in enumerate(section.subsections, 1):
                    sub_prefix = "  " * (subsection.level - 1)
                    print(f"{sub_prefix}└─ (Level {subsection.level}) {subsection.title}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(list_document_headings())
