# Canada.ca Chat Agent 🇨🇦

A production-grade, bilingual (English/French) RAG-based chat agent for Canada.ca.

## Features

- 🔍 **RAG-based responses** with source citations
- 🌐 **Bilingual support** (English & French)
- 🔒 **Security guardrails** (PII detection, prompt injection protection)
- 🔄 **Nightly content sync** with change detection
- ☁️ **Cloud-native** deployment on Azure (Canada region)
- 📊 **Observable** with comprehensive logging and monitoring

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, LangGraph, LangChain
- **Database**: PostgreSQL with pgvector
- **Cache**: Redis
- **LLM**: Azure OpenAI (GPT-4o) with configurable providers
- **Infrastructure**: Azure Container Apps, Terraform

## Quick Start

### Prerequisites

- Python 3.9+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- Docker & Docker Compose
- AWS Account with Bedrock access (or other LLM provider)

### Local Development

```bash
# Clone the repository
git clone <repo-url>
cd canada.ca

# Create virtual environment and install dependencies with uv
uv venv
uv pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Edit .env with your settings

# Set AWS credentials (choose one method):
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=ca-central-1

# Option 2: AWS CLI (recommended)
aws configure

# Start infrastructure (PostgreSQL, Redis)
docker-compose up -d

# Run database migrations
uv run python scripts/migrate_db.py

# Start the API
uv run uvicorn src.api.main:app --reload
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |
| `/api/v1/chat` | POST | Send chat message |
| `/api/v1/sessions/{id}` | GET | Get session history |

### Chat API Example

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I apply for a passport?",
    "session_id": null
  }'
```

## Project Structure

```
canada.ca/
├── docs/                    # Documentation
├── infrastructure/          # Terraform & Docker
├── src/                     # Application source
│   ├── api/                 # FastAPI routes
│   ├── agent/               # LangGraph agent
│   ├── llm/                 # LLM provider factory
│   ├── scraper/             # Web scraping
│   ├── security/            # Guardrails & PII
│   ├── vectorstore/         # pgvector integration
│   └── config/              # Settings
├── tests/                   # Test suite
├── frontend/                # Web UI
└── scripts/                 # Utility scripts
```

## Documentation

- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [API Documentation](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Security Guidelines](docs/SECURITY.md)

## License

Proprietary - All rights reserved

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
