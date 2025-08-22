#!/bin/bash
# 🚀 END OF DAY INDEXING SCRIPT FOR M1 ULTRA
# Run this when you're done working for the day!

echo "=================================================="
echo "🚀 RAG SLACK BOT - OVERNIGHT INDEXING"
echo "=================================================="
echo ""
echo "Configuration:"
echo "  - Model: Qwen 2.5 32B (19GB)"
echo "  - Embeddings: mxbai-embed-large" 
echo "  - Workers: 8 parallel threads"
echo "  - Target: 1GB of Google Docs"
echo ""
echo "=================================================="

# Start ChromaDB if not running
echo "1️⃣ Starting ChromaDB..."
docker-compose -f docker-compose.local.yml up -d

# Wait for ChromaDB to be ready
echo "   Waiting for ChromaDB to be ready..."
sleep 5

# Activate Python environment
echo "2️⃣ Activating Python environment..."
source .venv/bin/activate

# Run the Office file indexer (handles .docx, .xlsx, .pptx, .pdf)
echo "3️⃣ Starting parallel indexing..."
echo "   Processing Office files (.docx, .xlsx, .pptx, .pdf)"
echo "   This will take approximately 4-5 hours for ~1,100 documents"
echo ""
echo "📊 Progress will be displayed below:"
echo "=================================================="

# Run with time tracking
time python index_office_files.py

echo ""
echo "=================================================="
echo "✅ INDEXING COMPLETE!"
echo "=================================================="
echo ""
echo "Your documents are now searchable via Slack!"
echo "Start the bot with: python -m app.main"
echo ""