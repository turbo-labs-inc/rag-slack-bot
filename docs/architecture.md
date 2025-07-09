# Document Q&A Slack Bot Architecture

## Project Overview

An AI-powered Slack bot that intelligently answers questions about software documentation by referencing and linking to specific sections in Google Docs. The system uses vector embeddings and RAG (Retrieval Augmented Generation) to provide accurate, context-aware responses.

## Core Architecture Principles

- **Self-Hostable**: All components can run locally or in your own infrastructure
- **Provider Agnostic**: Support for multiple LLM providers (OpenAI, Gemini, Claude, Ollama)
- **Container-First**: Designed for Kubernetes/Docker deployment
- **Privacy-Conscious**: Option to run everything locally with Ollama

## System Architecture

```
[Slack] → [Slack Bolt App] → [Query Processing]
                ↓                      ↓
         [Admin Commands]      [Vector Search]
                ↓                      ↓
        [Doc Parser] ←─────→ [Vector Database]
                ↓
        [Google Docs API]
```

## Technology Stack

### Core Components

- **Language**: Python 3.11+
- **Slack Integration**: slack-bolt
- **Vector Database**: ChromaDB (self-hosted)
- **LLM Providers**: OpenAI/Gemini/Claude/Ollama
- **Document Access**: Google Docs API
- **Embeddings**: Sentence Transformers (local) or OpenAI
- **Container Runtime**: Docker/Kubernetes

### Python Dependencies

```python
slack-bolt==1.x          # Slack integration
google-api-python-client # Google Docs access
chromadb==0.4.x         # Vector database
sentence-transformers    # Embeddings
langchain==0.1.x        # LLM orchestration (optional)
fastapi==0.x            # API server (optional)
redis                   # Caching layer (future)
```

## Vector Database Strategy

### ChromaDB (Recommended for MVP)
- **Pros**: 
  - Fully open source (Apache 2.0)
  - Simple API, embedded or client-server mode
  - Built-in persistence
  - Easy Docker deployment: `docker run -p 8000:8000 chromadb/chroma`
- **Cons**: 
  - Less mature than alternatives
  - Limited scaling options

### Alternative Options
- **Qdrant**: More scalable, Rust-based, better production features
- **Milvus**: Enterprise-grade but complex
- **pgvector**: Good if already using PostgreSQL

## Document Processing & Chunking Strategy

### Smart Chunking Approach

Our chunking strategy combines structural and semantic understanding:

1. **Structural Parsing**: Parse documents by headers and sections
2. **Semantic Splitting**: Use LLM to identify logical boundaries in large sections
3. **Context Enrichment**: Generate summaries for each chunk
4. **Metadata Preservation**: Maintain section hierarchy and relationships

### Implementation

```python
class DocumentChunker:
    def __init__(self, llm_provider):
        self.llm = llm_provider
        
    async def chunk_document(self, doc_content):
        # 1. Parse by document structure (headers/sections)
        sections = self.parse_by_headers(doc_content)
        
        # 2. Smart-split long sections
        chunks = []
        for section in sections:
            if len(section['content']) > 1000:
                sub_chunks = await self.semantic_split(section)
                chunks.extend(sub_chunks)
            else:
                chunks.append(section)
        
        # 3. Enrich with metadata and summaries
        enriched_chunks = []
        for chunk in chunks:
            summary = await self.llm.summarize(chunk['content'])
            enriched_chunks.append({
                'content': chunk['content'],
                'summary': summary,
                'section': chunk['section_title'],
                'chunk_id': generate_id()
            })
        
        return enriched_chunks
```

### Embedding Strategy

- **Dual Embeddings**: Embed both content and LLM-generated summaries
- **Rich Metadata**: Store section hierarchy, timestamps, and relationships
- **Context Windows**: Include overlapping text from adjacent chunks

## LLM Provider Abstraction

### Design Pattern

```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        pass
    
    @abstractmethod
    async def generate_response(self, prompt: str, context: str) -> str:
        pass

class OllamaProvider(LLMProvider):
    # Local Ollama implementation

class OpenAIProvider(LLMProvider):
    # OpenAI API implementation

# Config-driven selection
llm = LLMProviderFactory.create(os.getenv("LLM_PROVIDER", "ollama"))
```

### Supported Providers

1. **Ollama** (Default for local development)
   - Fully self-hosted
   - No API costs
   - Privacy-preserving

2. **OpenAI**
   - High quality responses
   - Good for production
   - API costs apply

3. **Google Gemini**
   - Competitive pricing
   - Good performance

4. **Anthropic Claude**
   - Excellent for complex queries
   - Strong context understanding

## Query Processing Pipeline

### RAG Pipeline Flow

1. User sends query via Slack
2. Generate query embedding
3. Vector similarity search (top-k results)
4. Optional: Rerank results
5. Generate response with LLM + retrieved context
6. Format response with links to Google Doc sections
7. Send formatted response to Slack

### Response Format Example

```
User: "What's the basis price on a spot market?"

Bot: The basis price on a spot market is the differential between 
the local spot price and the futures settlement price (typically 
New York Harbor futures). This reflects the cost of physical 
delivery and local market conditions.

📍 Source: [Pricing Overview → Spot Markets → Basis Price](link)
```

## Deployment Architecture

### Docker Compose (Local Development)

```yaml
version: '3.8'

services:
  slack-bot:
    build: .
    ports:
      - "3000:3000"
    environment:
      - LLM_PROVIDER=${LLM_PROVIDER:-ollama}
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - SLACK_APP_TOKEN=${SLACK_APP_TOKEN}
      - GOOGLE_DOCS_ID=${GOOGLE_DOCS_ID}
      - CHROMA_HOST=chromadb
      - OLLAMA_HOST=ollama
    depends_on:
      - chromadb
      - ollama
    volumes:
      - ./app:/app
      - ./credentials:/credentials:ro

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chroma-data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-models:/root/.ollama

volumes:
  chroma-data:
  ollama-models:
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: doc-qa-bot
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: slack-bot
        image: your-registry/doc-qa-bot:latest
        env:
        - name: LLM_PROVIDER
          value: "ollama"
        - name: OLLAMA_HOST
          value: "http://ollama-service:11434"
        - name: CHROMA_HOST
          value: "http://chromadb-service:8000"
```

## Repository Structure

```
doc-qa-bot/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── README.md
├── docs/
│   └── architecture.md
├── app/
│   ├── main.py
│   ├── config.py
│   ├── chunking/
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   └── strategies.py
│   ├── embedding/
│   │   ├── __init__.py
│   │   └── vectorizer.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── ollama.py
│   │   ├── openai.py
│   │   └── gemini.py
│   ├── slack/
│   │   ├── __init__.py
│   │   ├── bot.py
│   │   └── commands.py
│   └── google_docs/
│       ├── __init__.py
│       └── client.py
└── scripts/
    ├── setup_ollama.sh
    └── index_docs.py
```

## Slack Commands

### User Commands
- `/ask [question]` - Ask a question about the documentation
- `/help` - Show available commands

### Admin Commands
- `/update-docs` - Re-parse and update document embeddings
- `/stats` - Show usage statistics
- `/clear-cache` - Clear conversation cache

## Development Workflow

### Initial Setup

1. Clone repository
2. Copy `.env.example` to `.env` and configure
3. Set up Google Docs API credentials
4. Configure Slack app (Bot Token, App Token)
5. Run `docker-compose up`

### Document Indexing

```bash
# Initial indexing
docker-compose run slack-bot python scripts/index_docs.py

# Or via Slack command
/update-docs
```

### Testing Locally

1. Use ngrok for Slack events: `ngrok http 3000`
2. Update Slack app with ngrok URL
3. Test in development Slack workspace

## Performance Considerations

### Chunking Optimization
- Chunk size: 512-1024 tokens optimal
- Overlap: 50-100 tokens for context
- Summary generation adds indexing time but improves retrieval

### Query Performance
- ChromaDB handles ~1M vectors efficiently
- Response time: <2 seconds typical
- Slack 3-second timeout handled with async processing

### Scaling Considerations
- Start with single instance
- Add Redis for conversation state when needed
- Consider Qdrant/Milvus for 10M+ vectors

## Security Considerations

1. **API Keys**: Store in environment variables or secrets manager
2. **Google Docs Access**: Use service account with read-only permissions
3. **Slack Verification**: Validate all incoming requests
4. **LLM Safety**: Implement prompt injection protection
5. **Data Privacy**: Option to run fully on-premise with Ollama

## Future Enhancements

### Phase 2 Features
- Multiple document support
- Follow-up questions with context
- User feedback collection
- Analytics dashboard

### Phase 3 Features
- Fine-tuned models for domain-specific answers
- Automatic document change detection
- Multi-language support
- Integration with other data sources

## Monitoring & Observability

### Key Metrics
- Query response time
- Embedding search accuracy
- LLM token usage
- Cache hit rate
- Error rates

### Logging Strategy
- Structured logging with context
- Query/response pairs for analysis
- Performance metrics
- Error tracking

## Cost Optimization

### Self-Hosted Components
- ChromaDB: Free
- Ollama: Free (requires GPU for speed)
- Slack Bot: Free tier available

### API Costs (Optional)
- OpenAI: ~$0.001 per query
- Google Docs: Free tier sufficient
- Gemini: Competitive pricing

### Optimization Tips
- Cache frequent queries
- Use local embeddings (Sentence Transformers)
- Batch document updates
- Implement rate limiting