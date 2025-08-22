#!/usr/bin/env python3
"""
Parallel document indexing for massive document collections.
Optimized for M1 Ultra with 16 performance cores.
"""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging
from datetime import datetime
import json

from google.oauth2 import service_account
from googleapiclient.discovery import build
import chromadb
from chromadb.config import Settings
import httpx

from app.config import get_settings
from app.llm.factory import create_llm_provider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Worker-%(thread)d] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ParallelIndexer:
    """Parallel document indexer optimized for M1 Ultra."""
    
    def __init__(self, num_workers: int = 8):
        """Initialize with specified number of parallel workers."""
        self.num_workers = num_workers
        self.settings = get_settings()
        self.stats = {
            "total_documents": 0,
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
        self.docs_service = build('docs', 'v1', credentials=creds)
        
    def _init_chromadb(self):
        """Initialize ChromaDB client."""
        self.chroma_client = chromadb.HttpClient(
            host=self.settings.chroma_host,
            port=self.settings.chroma_port
        )
        
        # Create or get collection
        try:
            self.collection = self.chroma_client.create_collection(
                name="documents",
                metadata={"description": "Document embeddings"}
            )
            logger.info("Created new ChromaDB collection")
        except:
            self.collection = self.chroma_client.get_collection("documents")
            logger.info(f"Using existing collection with {self.collection.count()} documents")
            
    def _init_llm(self):
        """Initialize LLM provider."""
        self.llm = create_llm_provider()
        logger.info(f"Using LLM: {self.settings.llm_provider}")
        logger.info(f"Embedding model: {self.settings.ollama_embedding_model}")
        
    async def index_folder(self, folder_id: str):
        """Index all documents in a Google Drive folder."""
        start_time = time.time()
        
        logger.info(f"🚀 Starting parallel indexing with {self.num_workers} workers")
        logger.info(f"📁 Indexing folder: {folder_id}")
        
        # Get all documents
        documents = self._get_all_documents(folder_id)
        self.stats["total_documents"] = len(documents)
        
        logger.info(f"📄 Found {len(documents)} documents to index")
        
        # Process documents in parallel
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Create async tasks for each document
            tasks = []
            for i, doc in enumerate(documents, 1):
                task = self._process_document_async(doc, i, len(documents))
                tasks.append(task)
            
            # Process all documents
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successes and errors
            for result in results:
                if isinstance(result, Exception):
                    self.stats["errors"].append(str(result))
        
        # Calculate final stats
        self.stats["total_time"] = time.time() - start_time
        self._print_summary()
        
    def _get_all_documents(self, folder_id: str, recursive: bool = True) -> List[Dict]:
        """Recursively get all documents from folder."""
        documents = []
        
        def scan_folder(fid: str, path: str = ""):
            # Get all items in folder
            page_token = None
            while True:
                response = self.drive_service.files().list(
                    q=f"'{fid}' in parents and trashed = false",
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token,
                    pageSize=1000
                ).execute()
                
                for file in response.get('files', []):
                    mime = file['mimeType']
                    
                    if 'folder' in mime and recursive:
                        # Recursively scan subfolder
                        scan_folder(file['id'], f"{path}/{file['name']}")
                    elif 'document' in mime or 'spreadsheet' in mime:
                        # Add document to list
                        documents.append({
                            'id': file['id'],
                            'name': file['name'],
                            'path': path,
                            'mime_type': mime
                        })
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
        
        scan_folder(folder_id)
        return documents
        
    async def _process_document_async(self, doc: Dict, index: int, total: int):
        """Process a single document asynchronously."""
        try:
            logger.info(f"[{index}/{total}] Processing: {doc['name']}")
            
            # Get document content
            if 'document' in doc['mime_type']:
                content = self._get_doc_content(doc['id'])
            else:
                content = self._get_sheet_content(doc['id'])
            
            # Chunk the document
            chunks = self._smart_chunk(content, doc['name'])
            self.stats["total_chunks"] += len(chunks)
            
            # Generate embeddings in parallel
            embedding_tasks = []
            for chunk in chunks:
                task = self.llm.generate_embedding(chunk['text'])
                embedding_tasks.append(task)
            
            embeddings = await asyncio.gather(*embedding_tasks)
            
            # Store in ChromaDB
            for i, (chunk, embedding_result) in enumerate(zip(chunks, embeddings)):
                self.collection.add(
                    embeddings=[embedding_result.embedding],
                    documents=[chunk['text']],
                    metadatas=[{
                        'document_id': doc['id'],
                        'document_name': doc['name'],
                        'chunk_index': i,
                        'path': doc['path']
                    }],
                    ids=[f"{doc['id']}_chunk_{i}"]
                )
            
            logger.info(f"✅ [{index}/{total}] Indexed {len(chunks)} chunks from {doc['name']}")
            
        except Exception as e:
            logger.error(f"❌ [{index}/{total}] Error processing {doc['name']}: {e}")
            raise e
            
    def _get_doc_content(self, doc_id: str) -> str:
        """Get Google Doc content."""
        doc = self.docs_service.documents().get(documentId=doc_id).execute()
        content = doc.get('body', {}).get('content', [])
        
        text = []
        for element in content:
            if 'paragraph' in element:
                for elem in element['paragraph']['elements']:
                    if 'textRun' in elem:
                        text.append(elem['textRun']['content'])
        
        return ''.join(text)
        
    def _get_sheet_content(self, sheet_id: str) -> str:
        """Get Google Sheet content (simplified)."""
        # For now, just return the sheet ID as placeholder
        return f"[Google Sheet: {sheet_id}]"
        
    def _smart_chunk(self, text: str, doc_name: str, chunk_size: int = 1000) -> List[Dict]:
        """Smart chunking that respects document structure."""
        chunks = []
        
        # Simple chunking for now - can be enhanced
        words = text.split()
        current_chunk = []
        
        for word in words:
            current_chunk.append(word)
            
            if len(' '.join(current_chunk)) > chunk_size:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'metadata': {'source': doc_name}
                })
                current_chunk = []
        
        # Add remaining text
        if current_chunk:
            chunks.append({
                'text': ' '.join(current_chunk),
                'metadata': {'source': doc_name}
            })
        
        return chunks if chunks else [{'text': text, 'metadata': {'source': doc_name}}]
        
    def _print_summary(self):
        """Print indexing summary."""
        print("\n" + "="*60)
        print("📊 INDEXING COMPLETE!")
        print("="*60)
        print(f"📄 Documents processed: {self.stats['total_documents']}")
        print(f"🧩 Total chunks created: {self.stats['total_chunks']}")
        print(f"⏱️  Total time: {self.stats['total_time']:.1f} seconds")
        print(f"⚡ Average time per doc: {self.stats['total_time']/max(1, self.stats['total_documents']):.1f}s")
        print(f"🚀 Throughput: {self.stats['total_chunks']/max(1, self.stats['total_time']):.1f} chunks/second")
        
        if self.stats['errors']:
            print(f"\n❌ Errors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:
                print(f"   - {error}")
        else:
            print("\n✅ No errors - perfect run!")
        print("="*60)


async def main():
    """Main entry point."""
    settings = get_settings()
    
    print("🚀 M1 ULTRA PARALLEL INDEXER")
    print("="*60)
    
    # Configuration
    WORKERS = 8  # Start conservative, can increase to 16
    FOLDER_ID = settings.google_drive_folder_id
    
    print(f"Workers: {WORKERS}")
    print(f"Folder: {FOLDER_ID}")
    print(f"LLM: {settings.ollama_model}")
    print(f"Embeddings: {settings.ollama_embedding_model}")
    print("="*60)
    
    # Create indexer
    indexer = ParallelIndexer(num_workers=WORKERS)
    
    # Start indexing
    await indexer.index_folder(FOLDER_ID)
    
    print("\n💡 TIP: Increase workers to 12 or 16 for faster indexing!")
    print("   Your M1 Ultra can handle it! 💪")


if __name__ == "__main__":
    asyncio.run(main())