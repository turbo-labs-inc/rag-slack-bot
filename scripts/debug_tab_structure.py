"""Debug script to see Google Docs tab structure."""

import json
from app.config import get_settings
from app.google_docs import GoogleDocsClient

def debug_tab_structure():
    """Debug the structure of tabs to find ID fields."""
    print("🔍 Debugging Google Docs Tab Structure")
    print("=" * 50)
    
    try:
        settings = get_settings()
        
        # Initialize Google Docs client
        docs_client = GoogleDocsClient(
            service_account_path=settings.google_service_account_key_path
        )
        
        # Fetch document with tabs
        print(f"📥 Fetching document: {settings.google_docs_id}")
        document = docs_client.get_document(settings.google_docs_id, include_tabs=True)
        
        if "tabs" in document:
            print(f"📑 Found {len(document['tabs'])} tabs")
            
            for i, tab in enumerate(document["tabs"][:3]):  # Show first 3 tabs
                print(f"\n📂 Tab {i+1} structure:")
                print(f"Keys: {list(tab.keys())}")
                
                if "tabProperties" in tab:
                    print(f"tabProperties keys: {list(tab['tabProperties'].keys())}")
                    print(f"tabProperties: {json.dumps(tab['tabProperties'], indent=2)}")
                
                # Look for any ID-like fields
                for key, value in tab.items():
                    if 'id' in key.lower():
                        print(f"ID field found: {key} = {value}")
                        
                print("-" * 30)
        else:
            print("❌ No tabs found in document")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_tab_structure()