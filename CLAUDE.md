# Document Q&A Slack Bot - Project Instructions

## Project Overview
This is a self-hosted Slack bot that answers questions about software documentation stored in Google Docs. It uses vector embeddings and RAG (Retrieval Augmented Generation) to provide accurate responses with links to relevant sections.

## Key Project Decisions

### Architecture Principles
- **Self-hostable first**: All components must be able to run locally with docker-compose
- **LLM Provider agnostic**: Support Ollama (local), OpenAI, Gemini, and Claude
- **Container-based**: Designed for Kubernetes deployment
- **Privacy-conscious**: Default to local components (Ollama + ChromaDB)

### Technology Stack
- **Language**: Python 3.11+
- **Vector DB**: ChromaDB (self-hosted, open source)
- **Slack**: slack-bolt framework
- **LLMs**: Abstract interface supporting multiple providers
- **Default LLM**: Ollama for local development

### Chunking Strategy
- Use LLM-assisted smart chunking that understands document structure
- Parse Google Docs by headers/sections first
- Generate summaries for each chunk to improve retrieval
- Embed both content and summaries for better search

### Development Approach
- Everything runs locally with `docker-compose up`
- No external dependencies required for basic functionality
- Progressive enhancement: start local, add cloud providers as needed

## Important Implementation Notes

### When implementing features:
1. Always maintain the LLM provider abstraction - don't hardcode to any specific provider
2. Ensure all components can run in docker-compose
3. Keep ChromaDB as the primary vector database
4. Follow the established project structure in docs/architecture.md

### Docker Compose Services:
- `slack-bot`: Main application
- `chromadb`: Vector database (port 8000)
- `ollama`: Local LLM (port 11434)

### Environment Variables:
- `LLM_PROVIDER`: ollama|openai|gemini|claude (default: ollama)
- `SLACK_BOT_TOKEN`: From Slack app configuration
- `SLACK_APP_TOKEN`: For Socket Mode
- `GOOGLE_DOCS_ID`: The document to index

### Slack Commands to Implement:
- `/ask [question]`: Main Q&A functionality
- `/update-docs`: Re-index the Google Doc
- `/help`: Show available commands

## Code Style Guidelines
- Use async/await for all I/O operations
- Implement proper error handling with user-friendly messages
- Keep the chunking logic modular and testable
- Use type hints throughout the codebase
- Use modern typing syntax not Dict[] but dict[] or Optional[Dict] becomes dict | None

## Testing Approach
- Test with Ollama locally before trying cloud providers
- Use a sample Google Doc for development
- Test chunking strategies with different document structures

## File Structure Reference
See `/home/jvogel/scratch/minion/docs/architecture.md` for complete repository structure and detailed architecture decisions.

## Useful CLI Tools
- You can use gh for github commands

## Python Development Recommendations
- Use uv and the latest python we can (3.15.5?) for modern python development

## Development Workflow
- Use ruff to reformat files before commiting

## Project Workflow Reminders
- Commit after measurable small progress