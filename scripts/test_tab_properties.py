"""Test script to inspect Google Docs tab properties and validate tab title extraction."""

import asyncio
import json
import logging

from app.config import get_settings
from app.google_docs import GoogleDocsClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def test_tab_properties():
    """Test Google Docs tab properties extraction."""
    print("🔍 Testing Google Docs Tab Properties")
    print("=" * 60)
    
    try:
        settings = get_settings()
        
        # Initialize Google Docs client
        docs_client = GoogleDocsClient(
            service_account_path=settings.google_service_account_key_path
        )
        
        # Fetch document
        print(f"📥 Fetching document: {settings.google_docs_id}")
        document = docs_client.get_document(settings.google_docs_id)
        
        print(f"📑 Document title: {document.get('title', 'No title')}")
        print()
        
        # Check if document has tabs
        tabs = document.get("tabs", [])
        if not tabs:
            print("❌ Document has no tabs")
            return
            
        print(f"📚 Found {len(tabs)} tabs")
        print("-" * 40)
        
        # Inspect each tab
        for i, tab in enumerate(tabs):
            print(f"\n🔖 Tab {i+1}:")
            print(f"   Raw tab keys: {list(tab.keys())}")
            
            # Tab properties
            tab_properties = tab.get("tabProperties", {})
            print(f"   Tab properties keys: {list(tab_properties.keys())}")
            print(f"   Tab properties: {json.dumps(tab_properties, indent=4)}")
            
            # Test our extraction methods
            print(f"\n   🧪 Testing extraction methods:")
            
            # Method 1: Direct title
            title = tab_properties.get("title")
            print(f"   - Direct title: {repr(title)}")
            
            # Method 2: Index-based
            index = tab_properties.get("index")
            if index is not None:
                index_title = f"Tab {index + 1}"
                print(f"   - Index-based title: {repr(index_title)}")
            else:
                print(f"   - Index-based title: None (no index)")
            
            # Method 3: Tab ID
            tab_id = tab_properties.get("tabId")
            print(f"   - Tab ID: {repr(tab_id)}")
            
            # Method 4: First paragraph (sample)
            document_tab = tab.get("documentTab", {})
            content = document_tab.get("body", {}).get("content", [])
            
            first_text = None
            for item in content[:5]:  # Check first 5 items
                if "paragraph" in item:
                    paragraph = item["paragraph"]
                    elements = paragraph.get("elements", [])
                    for element in elements:
                        text_run = element.get("textRun", {})
                        text = text_run.get("content", "").strip()
                        if text and len(text) > 1:  # Skip single chars like newlines
                            first_text = text
                            break
                    if first_text:
                        break
            
            if first_text:
                trimmed_text = first_text[:50] + "..." if len(first_text) > 50 else first_text
                print(f"   - First paragraph text: {repr(trimmed_text)}")
            else:
                print(f"   - First paragraph text: None")
            
            # Test what we'd actually use
            print(f"\n   🎯 What our current logic would choose:")
            if "title" in tab_properties and tab_properties["title"]:
                chosen = tab_properties["title"]
                method = "Direct title"
            elif "index" in tab_properties:
                chosen = f"Tab {tab_properties['index'] + 1}"
                method = "Index-based"
            elif first_text and len(first_text.strip()) < 100:
                chosen = first_text.strip()
                method = "First paragraph"
            else:
                chosen = "Untitled Tab"
                method = "Fallback"
            
            print(f"   ✅ Chosen: {repr(chosen)} (using {method})")
            
            # Check sections too
            sections_count = 0
            for item in content:
                if "paragraph" in item:
                    paragraph = item["paragraph"]
                    style = paragraph.get("paragraphStyle", {})
                    named_style = style.get("namedStyleType", "")
                    if "HEADING" in named_style:
                        sections_count += 1
            
            print(f"   📊 Found ~{sections_count} headings in this tab")
            
        print("\n" + "=" * 60)
        print("🎉 Tab properties inspection complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_tab_properties())