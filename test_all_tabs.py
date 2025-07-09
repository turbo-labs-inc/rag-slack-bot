"""Test script to list all tabs and their headings from the Google Docs document."""

import asyncio
from pathlib import Path

from app.google_docs import GoogleDocsClient, GoogleDocsParser


async def test_all_tabs():
    """Test accessing all tabs in the Google Docs document."""
    url = "https://docs.google.com/document/d/1zbZjXJP948_Ud6vNYGZ5-Kae9q456SHgRiSEtEX-J9M/edit?tab=t.pbxyea5hgyv7#heading=h.ua4i2dyops6a"

    credentials_path = Path("credentials/google-docs-service-account.json")
    client = GoogleDocsClient(service_account_path=credentials_path)
    parser = GoogleDocsParser()

    try:
        document_id = client.extract_document_id_from_url(url)
        print(f"📄 Document ID: {document_id}")

        # Get document with all tabs
        document = client.get_document(document_id, include_tabs=True)
        print(f"📋 Document Title: {document.get('title', 'Unknown')}")

        # Parse the document with tab support
        parsed_doc = parser.parse_document(document)

        print(f"\n🎯 Total sections found: {len(parsed_doc.sections)}")
        print("=" * 80)

        # Display all sections with their hierarchy
        for i, section in enumerate(parsed_doc.sections, 1):
            if section.level == 1:
                # This is likely a tab
                print(f"\n📑 TAB {i}: {section.title}")
                print(
                    f"   📊 Contains {len(section.subsections)} subsections and {len(section.elements)} direct elements"
                )

                # Show subsections (content within the tab)
                for j, subsection in enumerate(section.subsections, 1):
                    indent = "  " * (subsection.level - 1)
                    print(
                        f"   {indent}├─ Section {j}: {subsection.title} (Level {subsection.level})"
                    )

                    # Show preview of content
                    if subsection.elements:
                        preview = subsection.elements[0].text[:100].replace("\n", " ")
                        if len(subsection.elements[0].text) > 100:
                            preview += "..."
                        print(f"   {indent}   Preview: {preview}")

                    # Show nested subsections
                    for k, nested in enumerate(subsection.subsections, 1):
                        nested_indent = "  " * (nested.level - 1)
                        print(
                            f"   {nested_indent}   └─ Nested {k}: {nested.title} (Level {nested.level})"
                        )

            else:
                # This is a regular section (not a tab)
                indent = "  " * (section.level - 1)
                print(f"\n📄 {indent}Section {i}: {section.title} (Level {section.level})")
                print(f"   {indent}📊 Contains {len(section.elements)} elements")

                if section.elements:
                    preview = section.elements[0].text[:100].replace("\n", " ")
                    if len(section.elements[0].text) > 100:
                        preview += "..."
                    print(f"   {indent}Preview: {preview}")

        # Show document statistics
        print("\n" + "=" * 80)
        print("📊 DOCUMENT STATISTICS")
        print("=" * 80)

        full_text = parsed_doc.get_full_text()
        total_elements = sum(len(section.elements) for section in parsed_doc.sections)

        # Count tabs vs regular sections
        tab_count = sum(1 for section in parsed_doc.sections if section.level == 1)
        section_count = len(parsed_doc.sections) - tab_count

        print(f"📑 Total tabs: {tab_count}")
        print(f"📄 Total sections: {section_count}")
        print(f"📝 Total elements: {total_elements}")
        print(f"📏 Total characters: {len(full_text):,}")
        print(f"📊 Estimated words: {len(full_text.split()):,}")

        # List all tab titles
        tab_titles = [
            section.title for section in parsed_doc.sections if section.level == 1 and section.title
        ]
        if tab_titles:
            print(f"\n📑 TAB TITLES FOUND:")
            for i, title in enumerate(tab_titles, 1):
                print(f"   {i}. {title}")

        # Show raw document structure for debugging
        print(f"\n🔧 DEBUG INFO:")
        print(f"   Raw document keys: {list(document.keys())}")
        if "tabs" in document:
            print(f"   Tabs in document: {len(document['tabs'])}")
            for i, tab in enumerate(document["tabs"]):
                tab_props = tab.get("tabProperties", {})
                print(f"   Tab {i + 1} properties: {tab_props}")
        else:
            print("   No tabs field found in document")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_all_tabs())
