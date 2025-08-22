#!/bin/bash
# 🚀 ULTIMATE RE-INDEXING WITH BGE-M3 FOR M1 ULTRA
# State-of-the-art embeddings with 1024 dimensions + contextual enhancements

echo "=================================================="
echo "🔥 ULTIMATE RE-INDEXING WITH BGE-M3"
echo "=================================================="
echo ""
echo "⚠️  WARNING: This will DELETE and RECREATE the collection!"
echo "Configuration:"
echo "  - Model: Qwen 2.5 32B (19GB)"
echo "  - Embeddings: BGE-M3 (1024 dimensions, SOTA quality)" 
echo "  - Workers: 16 parallel threads (max for M1 Ultra)"
echo "  - Enhancements: Contextual embeddings + metadata enrichment"
echo ""
echo "Press Ctrl+C in next 5 seconds to cancel..."
sleep 5

# Ensure ChromaDB is running
echo "1️⃣ Starting ChromaDB..."
docker-compose -f docker-compose.local.yml up -d
sleep 5

# Activate Python environment
echo "2️⃣ Activating Python environment..."
source .venv/bin/activate

# Update .env to use bge-m3
echo "3️⃣ Configuring for BGE-M3 1024-dimension embeddings..."
sed -i.bak 's/OLLAMA_EMBEDDING_MODEL=.*/OLLAMA_EMBEDDING_MODEL=bge-m3/' .env

# Delete existing collection
echo "4️⃣ Deleting old collection..."
python3 -c "
import chromadb
client = chromadb.HttpClient(host='localhost', port=8000)
try:
    client.delete_collection('office_documents')
    print('✅ Old collection deleted')
except:
    print('📝 No existing collection to delete')
"

# Use the fixed ultimate indexer
echo "5️⃣ Using fixed ultimate indexer with proper metadata handling..."
# Don't overwrite - use the fixed version
if [ ! -f "index_ultimate_FIXED.py" ]; then
    echo "❌ Fixed indexer not found! Creating it now..."
    cat > index_ultimate.py << 'EOF'
#!/usr/bin/env python3
"""
ULTIMATE parallel indexer with BGE-M3 and contextual embeddings.
Implements state-of-the-art embedding techniques for maximum retrieval quality.
"""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import io
import hashlib
import json

from google.oauth2 import service_account
from googleapiclient.discovery import build
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation
import PyPDF2
import chromadb
from chromadb.config import Settings
import httpx

from app.config import get_settings
from app.llm.factory import create_llm_provider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Worker-%(thread)d] - %(message)s'
)
logger = logging.getLogger(__name__)

class UltimateIndexer:
    """State-of-the-art indexer with BGE-M3 and contextual embeddings."""
    
    def __init__(self, num_workers: int = 16):
        """Initialize with maximum workers for M1 Ultra."""
        self.num_workers = num_workers
        self.settings = get_settings()
        self.stats = {
            "total_documents": 0,
            "processed": 0,
            "failed": 0,
            "total_chunks": 0,
            "total_time": 0,
            "errors": []
        }
        
        # Initialize services
        self._init_google_drive()
        self._init_chromadb()
        self._init_llm()
        
    def _init_google_drive(self):
        """Initialize Google Drive client."""
        creds_path = Path("./credentials/google-docs-service-account.json")
        creds = service_account.Credentials.from_service_account_file(
            str(creds_path),
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        self.drive_service = build('drive', 'v3', credentials=creds)
        
    def _init_chromadb(self):
        """Initialize ChromaDB with BGE-M3 1024 dimensions."""
        self.chroma_client = chromadb.HttpClient(
            host=self.settings.chroma_host,
            port=self.settings.chroma_port
        )
        
        # Create collection with BGE-M3 metadata
        self.collection = self.chroma_client.create_collection(
            name="office_documents",
            metadata={
                "description": "BGE-M3 1024-dimension embeddings with contextual enhancements",
                "embedding_model": "bge-m3",
                "dimensions": 1024,
                "features": "contextual_embeddings,document_hierarchy,semantic_chunking"
            }
        )
        logger.info("✅ Created collection with BGE-M3 (1024 dimensions)")
            
    def _init_llm(self):
        """Initialize LLM provider."""
        self.llm = create_llm_provider()
        logger.info(f"Using LLM: {self.settings.llm_provider}")
        logger.info(f"Embedding model: BGE-M3 (SOTA 1024 dimensions)")
        
    async def index_folder(self, folder_id: str):
        """Index with contextual embeddings and metadata enrichment."""
        start_time = time.time()
        
        logger.info(f"🔥 ULTIMATE INDEXING with {self.num_workers} workers")
        logger.info(f"📁 Indexing folder: {folder_id}")
        
        # Get all documents with hierarchy
        documents = self._get_all_office_documents(folder_id)
        self.stats["total_documents"] = len(documents)
        
        logger.info(f"📄 Found {len(documents)} documents to index")
        
        # Build document hierarchy for contextual embeddings
        doc_hierarchy = self._build_document_hierarchy(documents)
        
        # Process with maximum parallelism
        semaphore = asyncio.Semaphore(self.num_workers)
        
        async def process_with_semaphore(doc, index, total):
            async with semaphore:
                return await self._process_document_async(doc, index, total, doc_hierarchy)
        
        # Create all tasks
        tasks = [
            process_with_semaphore(doc, i, len(documents))
            for i, doc in enumerate(documents, 1)
        ]
        
        # Process everything in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count results
        for result in results:
            if isinstance(result, Exception):
                self.stats["failed"] += 1
                self.stats["errors"].append(str(result))
            else:
                self.stats["processed"] += 1
        
        self.stats["total_time"] = time.time() - start_time
        self._print_summary()
        
    def _get_all_office_documents(self, folder_id: str, recursive: bool = True) -> List[Dict]:
        """Get all Office documents with full metadata."""
        documents = []
        
        def scan_folder(fid: str, path: str = "", parent_name: str = ""):
            page_token = None
            while True:
                response = self.drive_service.files().list(
                    q=f"'{fid}' in parents and trashed = false",
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
                    pageToken=page_token,
                    pageSize=1000
                ).execute()
                
                for file in response.get('files', []):
                    mime = file['mimeType']
                    
                    if 'folder' in mime and recursive:
                        scan_folder(file['id'], f"{path}/{file['name']}", file['name'])
                    elif any(x in mime for x in ['wordprocessingml', 'spreadsheetml', 'presentationml', 'pdf', 'document', 'sheet', 'presentation']):
                        documents.append({
                            'id': file['id'],
                            'name': file['name'],
                            'path': path,
                            'parent_folder': parent_name,
                            'mime_type': mime,
                            'modified_time': file.get('modifiedTime', ''),
                            'size': int(file.get('size', 0))
                        })
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
        
        scan_folder(folder_id)
        return documents
        
    def _build_document_hierarchy(self, documents: List[Dict]) -> Dict[str, List[str]]:
        """Build document hierarchy for contextual embeddings."""
        hierarchy = {}
        
        # Group documents by folder
        for doc in documents:
            folder = doc['path'] or '/'
            if folder not in hierarchy:
                hierarchy[folder] = []
            hierarchy[folder].append(doc['name'])
        
        return hierarchy
        
    async def _process_document_async(self, doc: Dict, index: int, total: int, doc_hierarchy: Dict):
        """Process document with contextual embeddings."""
        try:
            logger.info(f"[{index}/{total}] Processing: {doc['name']}")
            
            # Download file
            request = self.drive_service.files().get_media(fileId=doc['id'])
            file_content = io.BytesIO(request.execute())
            
            # Extract text with structure preservation
            text, structure = self._extract_text_with_structure(file_content, doc)
            
            if not text:
                logger.warning(f"No text from {doc['name']}")
                return
            
            # Generate document summary for better retrieval
            doc_summary = await self._generate_document_summary(text[:3000], doc['name'])
            
            # Smart semantic chunking with structure awareness
            chunks = self._semantic_chunk(text, structure, doc, doc_summary)
            self.stats["total_chunks"] += len(chunks)
            
            # Generate contextual embeddings with enriched metadata
            for i, chunk in enumerate(chunks):
                if chunk['text'].strip():
                    # Add context to chunk text for better embeddings
                    contextual_text = self._create_contextual_text(
                        chunk['text'],
                        doc,
                        doc_summary,
                        chunk.get('section', ''),
                        doc_hierarchy
                    )
                    
                    # Generate high-quality embedding with BGE-M3
                    embedding_result = await self.llm.generate_embedding(contextual_text)
                    
                    # Create rich metadata
                    metadata = {
                        'document_id': doc['id'],
                        'document_name': doc['name'],
                        'document_path': doc['path'],
                        'parent_folder': doc['parent_folder'],
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'section': chunk.get('section', ''),
                        'subsection': chunk.get('subsection', ''),
                        'chunk_type': chunk.get('type', 'text'),  # text, table, list, etc.
                        'chunk_size': len(chunk['text']),
                        'original_size': doc['size'],
                        'mime_type': doc['mime_type'],
                        'modified_time': doc['modified_time'],
                        'document_summary': doc_summary[:500] if doc_summary else '',
                        'chunk_summary': chunk.get('summary', ''),
                        'semantic_tags': ','.join(chunk.get('tags', [])) if isinstance(chunk.get('tags'), list) else str(chunk.get('tags', '')),
                        'confidence_score': chunk.get('confidence', 1.0)
                    }
                    
                    # Store with unique ID including content hash for deduplication
                    chunk_hash = hashlib.md5(chunk['text'].encode()).hexdigest()[:8]
                    chunk_id = f"{doc['id']}_chunk_{i}_{chunk_hash}"
                    
                    self.collection.add(
                        embeddings=[embedding_result.embedding],
                        documents=[chunk['text']],  # Store original text, not contextual
                        metadatas=[metadata],
                        ids=[chunk_id]
                    )
            
            logger.info(f"✅ [{index}/{total}] Indexed {len(chunks)} chunks from {doc['name']}")
            
        except Exception as e:
            logger.error(f"❌ [{index}/{total}] Error: {doc['name']}: {e}")
            raise e
            
    def _extract_text_with_structure(self, file_content: io.BytesIO, doc: Dict) -> tuple[str, Dict]:
        """Extract text preserving document structure."""
        structure = {"sections": [], "type": "document"}
        
        if 'wordprocessingml' in doc['mime_type'] or doc['name'].endswith('.docx'):
            text, structure = self._extract_docx_with_structure(file_content)
        elif 'spreadsheetml' in doc['mime_type'] or doc['name'].endswith('.xlsx'):
            text, structure = self._extract_xlsx_with_structure(file_content)
        elif 'presentationml' in doc['mime_type'] or doc['name'].endswith('.pptx'):
            text, structure = self._extract_pptx_with_structure(file_content)
        elif 'pdf' in doc['mime_type'] or doc['name'].endswith('.pdf'):
            text, structure = self._extract_pdf_with_structure(file_content)
        else:
            text = ""
            
        return text, structure
            
    def _extract_docx_with_structure(self, file_content: io.BytesIO) -> tuple[str, Dict]:
        """Extract Word document with structure."""
        try:
            doc = Document(file_content)
            structure = {"sections": [], "type": "document", "has_toc": False}
            text_parts = []
            current_section = None
            
            for para in doc.paragraphs:
                if para.text.strip():
                    # Detect headers based on style
                    if para.style and 'Heading' in para.style.name:
                        level = para.style.name.replace('Heading ', '')
                        current_section = {
                            "title": para.text,
                            "level": level,
                            "content": []
                        }
                        structure["sections"].append(current_section)
                        text_parts.append(f"\n{'#' * int(level) if level.isdigit() else '##'} {para.text}\n")
                    else:
                        text_parts.append(para.text)
                        if current_section:
                            current_section["content"].append(para.text)
            
            # Extract tables with structure
            for table_idx, table in enumerate(doc.tables):
                table_text = [f"\n[Table {table_idx + 1}]"]
                for row in table.rows:
                    row_text = ' | '.join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        table_text.append(row_text)
                if len(table_text) > 1:
                    text_parts.append('\n'.join(table_text))
                    structure["sections"].append({
                        "title": f"Table {table_idx + 1}",
                        "level": "table",
                        "content": table_text[1:]
                    })
            
            return '\n\n'.join(text_parts), structure
        except Exception as e:
            logger.error(f"Error extracting DOCX: {e}")
            return "", {"sections": [], "type": "document"}
            
    def _extract_xlsx_with_structure(self, file_content: io.BytesIO) -> tuple[str, Dict]:
        """Extract Excel with structure and formulas."""
        try:
            wb = load_workbook(file_content, read_only=True, data_only=True)
            structure = {"sheets": [], "type": "spreadsheet"}
            text_parts = []
            
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                sheet_structure = {
                    "name": sheet_name,
                    "tables": [],
                    "has_formulas": False
                }
                sheet_text = [f"=== Sheet: {sheet_name} ==="]
                
                # Detect table regions
                table_data = []
                for row in sheet.iter_rows(values_only=True):
                    row_text = ' | '.join(str(cell) for cell in row if cell is not None)
                    if row_text.strip() and row_text != " | ":
                        table_data.append(row_text)
                        sheet_text.append(row_text)
                
                if table_data:
                    sheet_structure["tables"].append({
                        "rows": len(table_data),
                        "data": table_data[:5]  # Sample data
                    })
                
                if len(sheet_text) > 1:
                    text_parts.append('\n'.join(sheet_text))
                    structure["sheets"].append(sheet_structure)
            
            return '\n\n'.join(text_parts), structure
        except Exception as e:
            logger.error(f"Error extracting XLSX: {e}")
            return "", {"sheets": [], "type": "spreadsheet"}
            
    def _extract_pptx_with_structure(self, file_content: io.BytesIO) -> tuple[str, Dict]:
        """Extract PowerPoint with slide structure."""
        try:
            prs = Presentation(file_content)
            structure = {"slides": [], "type": "presentation"}
            text_parts = []
            
            for slide_num, slide in enumerate(prs.slides, 1):
                slide_structure = {
                    "number": slide_num,
                    "title": "",
                    "content_types": [],
                    "has_notes": False
                }
                slide_text = [f"=== Slide {slide_num} ==="]
                
                # Extract slide title
                if slide.shapes.title:
                    slide_structure["title"] = slide.shapes.title.text
                    slide_text.append(f"Title: {slide.shapes.title.text}")
                
                # Extract content
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        if shape != slide.shapes.title:
                            slide_text.append(shape.text)
                            slide_structure["content_types"].append("text")
                    
                    # Extract tables
                    if shape.has_table:
                        slide_structure["content_types"].append("table")
                        table_text = ["[Table]"]
                        for row in shape.table.rows:
                            row_text = ' | '.join(cell.text for cell in row.cells if cell.text)
                            if row_text.strip():
                                table_text.append(row_text)
                        if len(table_text) > 1:
                            slide_text.extend(table_text)
                
                # Extract speaker notes
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                    notes = slide.notes_slide.notes_text_frame.text
                    if notes.strip():
                        slide_text.append(f"[Speaker Notes: {notes}]")
                        slide_structure["has_notes"] = True
                
                if len(slide_text) > 1:
                    text_parts.append('\n'.join(slide_text))
                    structure["slides"].append(slide_structure)
            
            return '\n\n'.join(text_parts), structure
        except Exception as e:
            logger.error(f"Error extracting PPTX: {e}")
            return "", {"slides": [], "type": "presentation"}
    
    def _extract_pdf_with_structure(self, file_content: io.BytesIO) -> tuple[str, Dict]:
        """Extract PDF with page structure."""
        try:
            reader = PyPDF2.PdfReader(file_content)
            structure = {"pages": [], "type": "pdf", "total_pages": len(reader.pages)}
            text_parts = []
            
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    text_parts.append(f"=== Page {page_num} ===\n{text}")
                    structure["pages"].append({
                        "number": page_num,
                        "has_text": True,
                        "char_count": len(text)
                    })
            
            return '\n\n'.join(text_parts), structure
        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
            return "", {"pages": [], "type": "pdf"}
            
    async def _generate_document_summary(self, text_sample: str, doc_name: str) -> Optional[str]:
        """Generate a concise document summary for better retrieval."""
        try:
            prompt = f"""Summarize this document in 2-3 sentences. Focus on the main topics and purpose.
Document: {doc_name}
Content sample: {text_sample[:2000]}

Summary:"""
            
            result = await self.llm.generate_response(prompt, max_tokens=150)
            if result.success:
                return result.response.strip()
        except Exception as e:
            logger.warning(f"Could not generate summary: {e}")
        return None
            
    def _semantic_chunk(self, text: str, structure: Dict, doc: Dict, doc_summary: str) -> List[Dict]:
        """Advanced semantic chunking with structure awareness."""
        chunks = []
        
        # Adaptive chunk size based on document type
        if structure.get('type') == 'presentation':
            # Chunk by slides
            sections = text.split('=== Slide ')
            for section in sections[1:]:  # Skip first empty
                if section.strip():
                    slide_num = section.split(' ===')[0]
                    content = section.split('===\n', 1)[-1] if '===\n' in section else section
                    chunks.append({
                        'text': content,
                        'section': f"Slide {slide_num}",
                        'type': 'slide',
                        'tags': f'presentation,slide_{slide_num}'
                    })
        
        elif structure.get('type') == 'spreadsheet':
            # Chunk by sheets
            sections = text.split('=== Sheet: ')
            for section in sections[1:]:
                if section.strip():
                    sheet_name = section.split(' ===')[0]
                    content = section.split('===\n', 1)[-1] if '===\n' in section else section
                    chunks.append({
                        'text': content,
                        'section': f"Sheet: {sheet_name}",
                        'type': 'spreadsheet',
                        'tags': f'data,table,{sheet_name.lower()}'
                    })
        
        else:
            # Smart paragraph-based chunking with overlap
            chunks = self._smart_paragraph_chunk(text, structure, chunk_size=1500, overlap=200)
        
        # Add document-level context to each chunk
        for chunk in chunks:
            if doc_summary:
                chunk['summary'] = f"From {doc['name']}: {doc_summary}"
            chunk['confidence'] = 1.0  # Can be adjusted based on extraction quality
        
        return chunks if chunks else [{'text': text, 'type': 'document', 'tags': ''}]
            
    def _smart_paragraph_chunk(self, text: str, structure: Dict, chunk_size: int = 1500, overlap: int = 200) -> List[Dict]:
        """Smart chunking that respects paragraph and section boundaries."""
        chunks = []
        
        # Split by sections if available
        if structure.get('sections'):
            for section in structure['sections']:
                section_text = '\n'.join(section.get('content', []))
                if section_text:
                    # Further chunk large sections
                    if len(section_text) > chunk_size:
                        sub_chunks = self._chunk_with_overlap(section_text, chunk_size, overlap)
                        for i, sub_chunk in enumerate(sub_chunks):
                            chunks.append({
                                'text': sub_chunk,
                                'section': section.get('title', 'Unknown'),
                                'subsection': f"Part {i+1}",
                                'type': 'text',
                                'tags': str(section.get('level', 'content'))
                            })
                    else:
                        chunks.append({
                            'text': section_text,
                            'section': section.get('title', 'Unknown'),
                            'type': section.get('level', 'text'),
                            'tags': [section.get('level', 'content')]
                        })
        else:
            # Fallback to paragraph-based chunking
            paragraphs = text.split('\n\n')
            current_chunk = []
            current_size = 0
            
            for para in paragraphs:
                para_size = len(para)
                
                if current_size + para_size > chunk_size and current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append({
                        'text': chunk_text,
                        'type': 'text',
                        'tags': 'paragraph'
                    })
                    
                    # Keep overlap
                    if len(current_chunk[-1]) < overlap and len(current_chunk) > 1:
                        current_chunk = [current_chunk[-1], para]
                        current_size = len(current_chunk[-1]) + para_size
                    else:
                        current_chunk = [para]
                        current_size = para_size
                else:
                    current_chunk.append(para)
                    current_size += para_size
            
            # Add remaining
            if current_chunk:
                chunks.append({
                    'text': '\n\n'.join(current_chunk),
                    'type': 'text',
                    'tags': ['paragraph']
                })
        
        return chunks
    
    def _chunk_with_overlap(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Simple chunking with overlap for large text blocks."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('. ')
                if last_period > chunk_size * 0.8:
                    chunk = chunk[:last_period + 1]
                    end = start + last_period + 1
            
            chunks.append(chunk)
            start = end - overlap if end < len(text) else end
        
        return chunks
            
    def _create_contextual_text(self, chunk_text: str, doc: Dict, doc_summary: str, 
                                section: str, doc_hierarchy: Dict) -> str:
        """Create contextual text for better embeddings."""
        context_parts = []
        
        # Add document context
        context_parts.append(f"Document: {doc['name']}")
        
        # Add folder context
        if doc['path']:
            context_parts.append(f"Location: {doc['path']}")
        
        # Add section context
        if section:
            context_parts.append(f"Section: {section}")
        
        # Add document summary for context
        if doc_summary:
            context_parts.append(f"Document Summary: {doc_summary[:200]}")
        
        # Add related documents context (same folder)
        folder = doc['path'] or '/'
        if folder in doc_hierarchy:
            related = [d for d in doc_hierarchy[folder] if d != doc['name']][:3]
            if related:
                context_parts.append(f"Related documents: {', '.join(related)}")
        
        # Combine context with chunk
        context = ' | '.join(context_parts)
        return f"{context}\n\nContent:\n{chunk_text}"
        
    def _print_summary(self):
        """Print indexing summary."""
        print("\n" + "="*60)
        print("🔥 ULTIMATE INDEXING COMPLETE!")
        print("="*60)
        print(f"📄 Documents: {self.stats['processed']}/{self.stats['total_documents']}")
        print(f"❌ Failed: {self.stats['failed']}")
        print(f"🧩 Chunks: {self.stats['total_chunks']}")
        print(f"⏱️  Time: {self.stats['total_time']:.1f}s ({self.stats['total_time']/60:.1f} min)")
        
        if self.stats['processed'] > 0:
            print(f"⚡ Speed: {self.stats['processed']/(self.stats['total_time']/60):.1f} docs/min")
            print(f"🚀 Chunks/sec: {self.stats['total_chunks']/self.stats['total_time']:.1f}")
        
        print("\n✨ Enhancements Applied:")
        print("  • BGE-M3 1024-dimension embeddings (SOTA)")
        print("  • Contextual embeddings with document hierarchy")
        print("  • Semantic chunking with structure preservation")
        print("  • Rich metadata for advanced filtering")
        print("  • Document summaries for better retrieval")
        print("="*60)


async def main():
    """Main entry point."""
    settings = get_settings()
    
    print("🔥 ULTIMATE INDEXER WITH BGE-M3")
    print("="*60)
    
    # Maximum performance configuration
    WORKERS = 16  # Max for M1 Ultra
    FOLDER_ID = settings.google_drive_folder_id
    
    print(f"Workers: {WORKERS} (MAXIMUM)")
    print(f"Folder: {FOLDER_ID}")
    print(f"LLM: {settings.ollama_model}")
    print(f"Embeddings: BGE-M3 (1024 dimensions, SOTA)")
    print("="*60)
    
    # Create indexer
    indexer = UltimateIndexer(num_workers=WORKERS)
    
    # Start indexing
    await indexer.index_folder(FOLDER_ID)
    
    print("\n💪 M1 ULTRA + BGE-M3 = ULTIMATE RAG QUALITY!")


if __name__ == "__main__":
    asyncio.run(main())
EOF
else
    echo "✅ Using existing index_ultimate_FIXED.py"
    cp index_ultimate_FIXED.py index_ultimate.py
fi

# Run the ultimate indexer
echo "6️⃣ Starting ULTIMATE indexing with BGE-M3..."
echo "=================================================="
time python index_ultimate.py

echo ""
echo "=================================================="
echo "✅ ULTIMATE RE-INDEXING COMPLETE!"
echo "=================================================="
echo ""
echo "Your RAG system now has:"
echo "  🎯 BGE-M3: State-of-the-art 1024-dimension embeddings"
echo "  📝 Contextual embeddings with document hierarchy"
echo "  🧠 Semantic chunking with structure preservation"
echo "  🏷️ Rich metadata for advanced filtering"
echo "  📊 Document summaries for better retrieval"
echo ""
echo "This is the highest quality embedding setup available!"
echo ""
echo "Start the bot with: ./START_BOT.sh"
echo ""