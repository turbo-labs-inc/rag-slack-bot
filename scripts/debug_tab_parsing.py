"""Debug script to see what happens during tab parsing."""

import asyncio
import logging

from app.config import get_settings
from app.google_docs import GoogleDocsClient, GoogleDocsParser

# Set up logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def debug_tab_parsing():
    """Debug tab parsing to see where tab names get lost."""
    print("🐛 Debugging Tab Parsing")
    print("=" * 40)
    
    try:
        settings = get_settings()
        
        # Initialize components
        docs_client = GoogleDocsClient(
            service_account_path=settings.google_service_account_key_path
        )
        docs_parser = GoogleDocsParser()
        
        # Fetch document
        print("📥 Fetching document...")
        document = docs_client.get_document(settings.google_docs_id)
        
        print(f"📑 Document: {document.get('title', 'No title')}")
        
        # Parse document and check what we get
        print("\n🔍 Parsing document...")
        parsed_doc = docs_parser.parse_document(document)
        
        print(f"📊 Total sections: {len(parsed_doc.sections)}")
        
        # Check first few sections to see their tab info
        print(f"\n📋 First 10 sections and their tab info:")
        for i, section in enumerate(parsed_doc.sections[:10]):
            print(f"   Section {i+1}: '{section.title}'")
            print(f"      tab_title: '{section.tab_title}'")
            print(f"      tab_id: '{section.tab_id}'")
            print(f"      level: {section.level}")
            
        # Count sections by tab
        tab_counts = {}
        empty_tab_count = 0
        
        for section in parsed_doc.sections:
            if section.tab_title:
                tab_counts[section.tab_title] = tab_counts.get(section.tab_title, 0) + 1
            else:
                empty_tab_count += 1
        
        print(f"\n📊 Sections by tab:")
        for tab_name, count in tab_counts.items():
            print(f"   '{tab_name}': {count} sections")
        
        if empty_tab_count:
            print(f"   ❌ Empty tab_title: {empty_tab_count} sections")
            
        # Check some sections with empty tab titles
        print(f"\n🔍 First 5 sections with empty tab_title:")
        empty_count = 0
        for i, section in enumerate(parsed_doc.sections):
            if not section.tab_title and empty_count < 5:
                print(f"   Section {i+1}: '{section.title}' (level {section.level})")
                empty_count += 1
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_tab_parsing())