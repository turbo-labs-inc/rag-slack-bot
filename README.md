# Document Q&A Slack Bot

An AI-powered Slack bot that intelligently answers questions about software documentation by referencing and linking to specific sections in Google Docs.

## Features

- 🤖 Natural language question answering
- 📄 Google Docs integration
- 🔍 Semantic search using vector embeddings
- 🔗 Direct links to relevant documentation sections
- 🏠 Self-hostable with Docker
- 🎯 Multiple LLM provider support (Ollama, OpenAI, Gemini, Claude)

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/gravitate-energy/doc-qa-slack-bot.git
cd doc-qa-slack-bot
```

2. Copy the environment template:
```bash
cp .env.example .env
```

3. Configure your `.env` file with:
   - Slack bot tokens
   - Google Docs ID
   - LLM provider settings

4. Start the services:
```bash
docker-compose up
```

## Development Setup

This project uses `uv` for Python dependency management and requires Python 3.13+.

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Watch tests
ptw

# Format code
ruff format .

# Lint code
ruff check .
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

## Implementation Plan

See [docs/implementation-plan.md](docs/implementation-plan.md) for the development roadmap.

## License

[Add your license here]