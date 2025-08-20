# RAG Slack Bot - Setup Checklist

## Current Status

### ✅ What's Ready:
1. **Slack Credentials** - Bot and App tokens configured
2. **Google Drive Folder ID** - Ready to index documents
3. **Local Llama 3.2** - Running on port 11434 with nomic embeddings
4. **ChromaDB** - Vector database configured with persistent storage
5. **Environment Config** - .env file fully configured

### 🔧 What's Missing:

#### 1. **Google Service Account Credentials**
You need to create a service account JSON file at:
```
./credentials/google-docs-service-account.json
```

To get this:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Drive API and Google Docs API
4. Create a Service Account
5. Download the JSON key file
6. Save it as `./credentials/google-docs-service-account.json`
7. Share your Google Drive folder with the service account email

#### 2. **Vector Database Location**
ChromaDB data is stored in:
- **Docker**: `chroma-data` volume (production)
- **Local Dev**: `./chroma_db/` directory (development)

## Quick Start Commands

### For Local Development:
```bash
# 1. Start ChromaDB only (Ollama already running locally)
docker-compose -f docker-compose.local.yml up -d

# 2. Activate Python environment
source .venv/bin/activate

# 3. Run the bot
python -m app.main
```

### For Full Docker Stack:
```bash
# Start everything in Docker
docker-compose up -d
```

## Test Your Setup:
```bash
# Test Llama integration
python test_llama_integration.py

# Check ChromaDB is running
curl http://localhost:8000/api/v1/heartbeat
```

## Switching LLM Providers:
Edit `.env` and change `LLM_PROVIDER`:
- `ollama` - Local Llama (FREE, current setting)
- `openai` - OpenAI GPT (costs money)
- `anthropic` - Claude (costs money)

## Data Flow:
1. **Google Drive** → Documents fetched via service account
2. **Document Processing** → Chunked into sections
3. **Embeddings** → Generated using nomic-embed-text (local)
4. **ChromaDB** → Vectors stored persistently
5. **User Query** → Embedded and searched in ChromaDB
6. **Context Retrieval** → Top relevant chunks retrieved
7. **Llama 3.2** → Generates response with context
8. **Slack** → Response sent back to user