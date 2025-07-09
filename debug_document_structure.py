"""Debug script to examine the full document structure and find tabs."""

import asyncio
import json
from pathlib import Path

from app.google_docs import GoogleDocsClient, GoogleDocsParser


async def debug_document_structure():
    """Debug the full document structure to understand tabs."""
    url = "https://docs.google.com/document/d/1zbZjXJP948_Ud6vNYGZ5-Kae9q456SHgRiSEtEX-J9M/edit?tab=t.pbxyea5hgyv7#heading=h.ua4i2dyops6a"

    credentials_path = Path("credentials/google-docs-service-account.json")
    client = GoogleDocsClient(service_account_path=credentials_path)

    try:
        document_id = client.extract_document_id_from_url(url)
        print(f"📄 Document ID: {document_id}")

        # Get the full document
        document = client.get_document(document_id)

        # Print high-level structure
        print(f"📋 Document Title: {document.get('title', 'Unknown')}")
        print(f"🔧 Top-level keys: {list(document.keys())}")

        # Look for tabs/sections in the document structure
        print("\n🔍 Analyzing document structure...")

        # Check if there are tabs mentioned anywhere
        doc_str = json.dumps(document, indent=2)
        if "tab" in doc_str.lower():
            print("✅ Found 'tab' references in document")
        else:
            print("❌ No 'tab' references found")

        # Check for section breaks
        content = document.get("body", {}).get("content", [])
        print(f"\n📊 Body content has {len(content)} items")

        section_breaks = []
        for i, item in enumerate(content):
            if "sectionBreak" in item:
                section_breaks.append(i)
                section_break = item["sectionBreak"]
                print(f"🔗 Section break at index {i}: {section_break}")

        print(f"\n📈 Found {len(section_breaks)} section breaks")

        # Look for any named sections or tabs
        if "namedRanges" in document:
            print(f"🏷️  Named ranges: {document['namedRanges']}")
        else:
            print("❌ No named ranges found")

        if "lists" in document:
            print(f"📝 Lists: {len(document['lists'])} lists found")
        else:
            print("❌ No lists found")

        # Check document styles for any tab indicators
        if "documentStyle" in document:
            doc_style = document["documentStyle"]
            print(f"🎨 Document style keys: {list(doc_style.keys())}")

        # Look at headers and footers
        if "headers" in document:
            print(f"📄 Headers: {len(document['headers'])} found")
            for header_id, header in document["headers"].items():
                print(f"   Header {header_id}: {header}")

        if "footers" in document:
            print(f"📄 Footers: {len(document['footers'])} found")
            for footer_id, footer in document["footers"].items():
                print(f"   Footer {footer_id}: {footer}")

        # Print first few content items to see structure
        print(f"\n📝 First 5 content items:")
        for i, item in enumerate(content[:5]):
            print(f"Item {i}: {list(item.keys())}")
            if "paragraph" in item:
                para = item["paragraph"]
                elements = para.get("elements", [])
                if elements and "textRun" in elements[0]:
                    text = elements[0]["textRun"].get("content", "")[:100]
                    print(f"   Text: {text}")

        # Let's also check the full text length
        parser = GoogleDocsParser()
        parsed_doc = parser.parse_document(document)
        full_text = parsed_doc.get_full_text()

        print(f"\n📏 Parsed document stats:")
        print(f"   Total characters: {len(full_text)}")
        print(f"   Total words: {len(full_text.split())}")
        print(f"   Total sections: {len(parsed_doc.sections)}")

        # Print the section titles we found
        print(f"\n📋 Section titles found:")
        for i, section in enumerate(parsed_doc.sections):
            if section.title:
                print(f"   {i + 1}. {section.title}")

        # Save the raw document to file for inspection
        with open("debug_document.json", "w") as f:
            json.dump(document, f, indent=2)
        print(f"\n💾 Full document saved to debug_document.json")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_document_structure())
