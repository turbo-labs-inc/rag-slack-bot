"""Read and display Google Doc content for analysis."""

import logging
from pathlib import Path

from app.config import get_settings
from app.google_docs import GoogleDocsClient, GoogleDocsParser

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_document_content():
    """Read the Google Doc and display its content."""
    print("📄 Reading Google Doc Content")
    print("=" * 50)
    
    try:
        settings = get_settings()
        
        # Initialize Google Docs components
        print("📄 Initializing Google Docs client...")
        docs_client = GoogleDocsClient(
            service_account_path=settings.google_service_account_key_path
        )
        docs_parser = GoogleDocsParser()
        
        # Fetch document
        print(f"📥 Fetching document: {settings.google_docs_id}")
        document = docs_client.get_document(settings.google_docs_id)
        parsed_doc = docs_parser.parse_document(document)
        
        print(f"📑 Document: {parsed_doc.title}")
        print(f"📊 Found {len(parsed_doc.sections)} total sections")
        print("\n" + "=" * 50)
        
        # Show first few sections to understand structure
        for i, section in enumerate(parsed_doc.sections[:10]):
            print(f"\n📄 Section {i+1}: {section.title}")
            print(f"Level: {section.level}")
            
            # Get section content
            content = section.get_full_text()
            print(f"Content ({len(content)} chars):")
            
            # Show first 400 characters of content
            preview = content[:400]
            if len(content) > 400:
                preview += "..."
                
            print(f"   {preview}")
            
            if len(content) > 400:
                print(f"   [... {len(content) - 400} more characters]")
        
        # Show some key sections that might contain company info
        print("\n" + "=" * 50)
        print("🔍 Looking for key sections...")
        
        for section in parsed_doc.sections:
            title_lower = section.title.lower()
            if any(keyword in title_lower for keyword in ['purpose', 'overview', 'introduction', 'getting started', 'features']):
                print(f"\n📍 KEY SECTION: {section.title}")
                content = section.get_full_text()
                print(f"   Content: {content[:500]}...")
                if len(content) > 500:
                    print(f"   [... {len(content) - 500} more characters]")
        
        print("\n" + "=" * 50)
        print("✅ Document content displayed above")
        
    except Exception as e:
        print(f"❌ Error reading document: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    read_document_content()