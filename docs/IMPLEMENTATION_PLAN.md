# Canada.ca Chat Agent - Implementation Plan

> **Project**: RAG-based Bilingual Chat Agent for Canada.ca
> **Created**: January 31, 2026
> **Status**: Planning Phase

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Phase 1: Foundation](#phase-1-foundation)
6. [Phase 2: Scraping & Ingestion Pipeline](#phase-2-scraping--ingestion-pipeline)
7. [Phase 3: Agent Intelligence](#phase-3-agent-intelligence)
8. [Phase 4: Security & Guardrails](#phase-4-security--guardrails)
9. [Phase 5: Production Hardening](#phase-5-production-hardening)
10. [Phase 6: Cloud Deployment](#phase-6-cloud-deployment)
11. [Phase 7: Analytics & Iteration](#phase-7-analytics--iteration)
12. [Cost Estimation](#cost-estimation)
13. [Risk Mitigation](#risk-mitigation)

---

## Executive Summary

### Goals
- Build a **production-grade bilingual chat agent** (English/French) for canada.ca
- Provide accurate, cited responses using **RAG (Retrieval Augmented Generation)**
- Support **nightly content scraping** with change detection
- Ensure **PII protection** and content guardrails
- Deploy to **Azure (Canada region)** with auto-scaling

### Key Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Cloud Provider | Azure (Canada Central/East) | Canada data residency |
| Primary LLM | Azure OpenAI (GPT-4o) | Canada East region available |
| Vector Database | PostgreSQL + pgvector | Cost-effective, single DB for all data |
| Container Orchestration | Azure Container Apps | Serverless, auto-scaling, cost-effective |
| Framework | LangGraph + LangChain + FastAPI | As specified |

### Target Metrics
| Metric | Target |
|--------|--------|
| Initial Query Volume | 100 queries/day |
| Response Latency | < 3 seconds (p95) |
| Availability | 99.5% uptime |
| Languages | English, French |
| Concurrent Users | Scalable to hundreds |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AZURE CLOUD (CANADA CENTRAL)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────────────────────┐  │
│  │   Azure CDN  │────▶│           Azure Container Apps                   │  │
│  │  (Frontend)  │     │  ┌────────────────┐  ┌────────────────────────┐  │  │
│  └──────────────┘     │  │   Web UI       │  │   FastAPI Backend      │  │  │
│                       │  │   (Static)     │  │   ┌────────────────┐   │  │  │
│                       │  └────────────────┘  │   │  LangGraph     │   │  │  │
│                       │                      │   │  Agent         │   │  │  │
│                       │                      │   └───────┬────────┘   │  │  │
│                       │                      └───────────┼────────────┘  │  │
│                       └──────────────────────────────────┼───────────────┘  │
│                                                          │                   │
│  ┌───────────────────────────────────────────────────────┼───────────────┐  │
│  │                     DATA LAYER                        │               │  │
│  │                                                       ▼               │  │
│  │  ┌─────────────────────┐    ┌─────────────────────────────────────┐  │  │
│  │  │  Azure Database     │    │         Azure OpenAI                │  │  │
│  │  │  for PostgreSQL     │    │         (Canada East)               │  │  │
│  │  │  ┌───────────────┐  │    │  ┌──────────┐  ┌─────────────────┐  │  │  │
│  │  │  │   pgvector    │  │    │  │  GPT-4o  │  │  text-embedding │  │  │  │
│  │  │  │   (Vectors)   │  │    │  │  (Chat)  │  │  -3-large       │  │  │  │
│  │  │  ├───────────────┤  │    │  └──────────┘  └─────────────────┘  │  │  │
│  │  │  │   Sessions    │  │    └─────────────────────────────────────┘  │  │
│  │  │  ├───────────────┤  │                                             │  │
│  │  │  │   Documents   │  │    ┌─────────────────────────────────────┐  │  │
│  │  │  └───────────────┘  │    │         Azure Cache for Redis       │  │  │
│  │  └─────────────────────┘    │  ┌───────────┐  ┌────────────────┐  │  │  │
│  │                             │  │  Response │  │  Rate Limiting │  │  │  │
│  │                             │  │  Cache    │  │                │  │  │  │
│  │                             │  └───────────┘  └────────────────┘  │  │  │
│  │                             └─────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     INGESTION PIPELINE                                │  │
│  │                                                                       │  │
│  │  ┌────────────────┐    ┌────────────────┐    ┌────────────────────┐  │  │
│  │  │  Azure         │───▶│  Scraper       │───▶│  Embeddings +      │  │  │
│  │  │  Functions     │    │  Container     │    │  Vector Storage    │  │  │
│  │  │  (Timer: 2am)  │    │  Job           │    │                    │  │  │
│  │  └────────────────┘    └────────────────┘    └────────────────────┘  │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     OBSERVABILITY                                     │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐  │  │
│  │  │  Application   │  │  LangSmith     │  │  Azure Monitor         │  │  │
│  │  │  Insights      │  │  (LLM Tracing) │  │  (Dashboards/Alerts)   │  │  │
│  │  └────────────────┘  └────────────────┘  └────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────┐
                    │           canada.ca                 │
                    │         (Source Website)            │
                    └─────────────────────────────────────┘
```

---

## Technology Stack

### Core Framework
| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.11+ |
| Agent Framework | LangGraph | Latest |
| LLM Abstraction | LangChain | Latest |
| API Framework | FastAPI | 0.109+ |
| Async Runtime | uvicorn + asyncio | Latest |

### LLM Providers (Factory Pattern)
| Provider | Model | Use Case |
|----------|-------|----------|
| Azure OpenAI | gpt-4o | Primary (Canada East) |
| Azure OpenAI | gpt-4o-mini | Cost-optimized fallback |
| OpenAI Direct | gpt-4o | Alternative testing |
| Anthropic | claude-3-sonnet | Alternative testing |

### Database & Storage
| Component | Technology | Purpose |
|-----------|------------|---------|
| Vector Store | PostgreSQL + pgvector | Embeddings storage |
| Session Store | PostgreSQL | Conversation history |
| Document Store | PostgreSQL | Scraped content metadata |
| Cache | Redis | Response caching, rate limiting |
| Blob Storage | Azure Blob Storage | Raw HTML archives |

### Infrastructure (Azure)
| Component | Service | Notes |
|-----------|---------|-------|
| Compute | Azure Container Apps | Auto-scaling, serverless |
| Database | Azure Database for PostgreSQL Flexible | pgvector enabled |
| Cache | Azure Cache for Redis | Basic tier initially |
| Secrets | Azure Key Vault | API keys, connection strings |
| Monitoring | Application Insights | APM + LangSmith for LLM |
| CI/CD | GitHub Actions | Automated deployments |
| IaC | Terraform | Infrastructure as Code |

### Security & Guardrails
| Component | Technology | Purpose |
|-----------|------------|---------|
| PII Detection | Microsoft Presidio | Detect/redact PII |
| Input Validation | Pydantic | Schema validation |
| Rate Limiting | Redis + custom middleware | Abuse prevention |
| Prompt Injection | LangChain guardrails | Protect LLM |
| Content Moderation | Azure Content Safety | Output filtering |

---

## Project Structure

```
canada.ca/
├── .github/
│   └── workflows/
│       ├── ci.yml                  # CI pipeline
│       ├── cd-staging.yml          # Deploy to staging
│       └── cd-production.yml       # Deploy to production
│
├── docs/
│   ├── IMPLEMENTATION_PLAN.md      # This document
│   ├── API.md                      # API documentation
│   ├── DEPLOYMENT.md               # Deployment guide
│   └── SECURITY.md                 # Security guidelines
│
├── infrastructure/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── modules/
│   │   │   ├── container-apps/
│   │   │   ├── postgresql/
│   │   │   ├── redis/
│   │   │   └── keyvault/
│   │   └── environments/
│   │       ├── dev.tfvars
│   │       ├── staging.tfvars
│   │       └── prod.tfvars
│   └── docker/
│       ├── Dockerfile.api
│       ├── Dockerfile.scraper
│       └── docker-compose.yml      # Local development
│
├── src/
│   ├── __init__.py
│   │
│   ├── api/                        # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py             # Chat endpoints
│   │   │   ├── health.py           # Health checks
│   │   │   └── admin.py            # Admin endpoints
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── rate_limiter.py
│   │   │   ├── request_id.py
│   │   │   └── language_detector.py
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── chat.py             # Pydantic models
│   │       └── common.py
│   │
│   ├── agent/                      # LangGraph Agent
│   │   ├── __init__.py
│   │   ├── graph.py                # Main agent graph
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── retriever.py        # RAG retrieval
│   │   │   ├── generator.py        # Response generation
│   │   │   ├── router.py           # Query routing
│   │   │   └── guardrails.py       # Safety checks
│   │   ├── state.py                # Agent state definition
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── system_en.py
│   │       ├── system_fr.py
│   │       └── templates.py
│   │
│   ├── llm/                        # LLM Provider Factory
│   │   ├── __init__.py
│   │   ├── factory.py              # Provider factory
│   │   ├── base.py                 # Abstract base class
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── azure_openai.py
│   │   │   ├── openai.py
│   │   │   └── anthropic.py
│   │   └── embeddings/
│   │       ├── __init__.py
│   │       ├── factory.py
│   │       └── providers/
│   │           ├── azure_openai.py
│   │           └── openai.py
│   │
│   ├── vectorstore/                # Vector Store
│   │   ├── __init__.py
│   │   ├── pgvector.py             # pgvector implementation
│   │   └── retriever.py            # Retrieval logic
│   │
│   ├── scraper/                    # Web Scraping
│   │   ├── __init__.py
│   │   ├── crawler.py              # Main crawler
│   │   ├── parser.py               # HTML parsing
│   │   ├── chunker.py              # Text chunking
│   │   ├── change_detector.py      # Detect content changes
│   │   └── scheduler.py            # Scheduling logic
│   │
│   ├── security/                   # Security & Guardrails
│   │   ├── __init__.py
│   │   ├── pii_detector.py         # PII detection (Presidio)
│   │   ├── input_validator.py      # Input validation
│   │   ├── prompt_guard.py         # Prompt injection protection
│   │   └── content_moderator.py    # Output moderation
│   │
│   ├── db/                         # Database
│   │   ├── __init__.py
│   │   ├── connection.py           # Connection pooling
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── document.py
│   │   │   ├── session.py
│   │   │   └── vector.py
│   │   └── migrations/             # Alembic migrations
│   │       └── versions/
│   │
│   ├── cache/                      # Caching
│   │   ├── __init__.py
│   │   └── redis_cache.py
│   │
│   └── config/                     # Configuration
│       ├── __init__.py
│       ├── settings.py             # Pydantic settings
│       └── logging.py              # Logging config
│
├── frontend/                       # Web UI
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── app.js
│   │   └── api.js
│   └── assets/
│       └── images/
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   ├── unit/
│   │   ├── test_agent.py
│   │   ├── test_scraper.py
│   │   └── test_security.py
│   ├── integration/
│   │   ├── test_api.py
│   │   └── test_vectorstore.py
│   └── e2e/
│       └── test_chat_flow.py
│
├── scripts/
│   ├── seed_data.py                # Initial data seeding
│   ├── run_scraper.py              # Manual scraper trigger
│   └── migrate_db.py               # Database migrations
│
├── .env.example                    # Environment template
├── .gitignore
├── pyproject.toml                  # Poetry/pip config
├── requirements.txt                # Dependencies
├── requirements-dev.txt            # Dev dependencies
└── README.md
```

---

## Phase 1: Foundation

**Duration**: Week 1-2
**Goal**: Basic working chat agent with local development environment

### Tasks

#### 1.1 Project Setup
- [ ] Initialize Python project with Poetry/pip
- [ ] Configure linting (ruff), formatting (black), type checking (mypy)
- [ ] Set up pre-commit hooks
- [ ] Create `.env.example` with all required variables

```python
# pyproject.toml dependencies
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "langchain>=0.1.0",
    "langgraph>=0.0.20",
    "langchain-openai>=0.0.5",
    "langchain-community>=0.0.20",
    "pgvector>=0.2.4",
    "sqlalchemy[asyncio]>=2.0.25",
    "asyncpg>=0.29.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "redis>=5.0.0",
    "httpx>=0.26.0",
    "beautifulsoup4>=4.12.0",
    "python-dotenv>=1.0.0",
]
```

#### 1.2 Configuration Management
- [ ] Implement Pydantic Settings for config
- [ ] Support for environment-specific configs
- [ ] Secrets management abstraction

```python
# src/config/settings.py
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # LLM Provider
    llm_provider: Literal["azure_openai", "openai", "anthropic"] = "azure_openai"
    
    # Azure OpenAI
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment_name: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-large"
    azure_openai_api_version: str = "2024-02-01"
    
    # OpenAI (alternative)
    openai_api_key: str | None = None
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Security
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 3600
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

#### 1.3 LLM Provider Factory
- [ ] Abstract base class for LLM providers
- [ ] Azure OpenAI implementation
- [ ] OpenAI direct implementation
- [ ] Anthropic implementation
- [ ] Factory for runtime selection

```python
# src/llm/factory.py
from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel
from src.config import settings

class LLMProviderFactory:
    @staticmethod
    def create_chat_model() -> BaseChatModel:
        if settings.llm_provider == "azure_openai":
            from langchain_openai import AzureChatOpenAI
            return AzureChatOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                deployment_name=settings.azure_openai_deployment_name,
                api_version=settings.azure_openai_api_version,
                temperature=0.1,
            )
        elif settings.llm_provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                api_key=settings.openai_api_key,
                model="gpt-4o",
                temperature=0.1,
            )
        elif settings.llm_provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model="claude-3-sonnet-20240229",
                temperature=0.1,
            )
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
```

#### 1.4 Database Setup
- [ ] PostgreSQL with pgvector extension
- [ ] SQLAlchemy async models
- [ ] Alembic migrations
- [ ] Connection pooling

```python
# src/db/models.py
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import ARRAY
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(String)
    content = Column(Text)
    content_hash = Column(String)  # For change detection
    language = Column(String(2))  # 'en' or 'fr'
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"))
    content = Column(Text)
    embedding = Column(Vector(3072))  # text-embedding-3-large dimension
    chunk_index = Column(Integer)
    metadata = Column(JSON)

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    language = Column(String(2))
    metadata = Column(JSON)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"))
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    sources = Column(JSON)  # Citation information
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### 1.5 Basic FastAPI Application
- [ ] Health check endpoint
- [ ] Chat endpoint (simple)
- [ ] CORS configuration
- [ ] Request ID middleware

```python
# src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import chat, health
from src.api.middleware import RequestIdMiddleware

app = FastAPI(
    title="Canada.ca Chat Agent",
    description="Bilingual RAG-based chat agent for canada.ca",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)

app.include_router(health.router, tags=["health"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
```

#### 1.6 Basic LangGraph Agent
- [ ] Simple RAG graph
- [ ] State definition
- [ ] Retriever node
- [ ] Generator node

```python
# src/agent/graph.py
from langgraph.graph import StateGraph, END
from src.agent.state import AgentState
from src.agent.nodes import retriever, generator

def create_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("retrieve", retriever.retrieve)
    graph.add_node("generate", generator.generate)
    
    # Add edges
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    
    # Set entry point
    graph.set_entry_point("retrieve")
    
    return graph.compile()
```

#### 1.7 Local Development Environment
- [ ] Docker Compose with PostgreSQL + Redis
- [ ] Local development instructions
- [ ] Sample data seeding

```yaml
# infrastructure/docker/docker-compose.yml
version: '3.8'

services:
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_DB: canadaca
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build:
      context: ../..
      dockerfile: infrastructure/docker/Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/canadaca
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
```

### Phase 1 Deliverables
- [ ] Working local development environment
- [ ] Basic chat API responding (even without real data)
- [ ] Database schema created
- [ ] LLM provider factory working with Azure OpenAI
- [ ] Unit tests for core components

---

## Phase 2: Scraping & Ingestion Pipeline

**Duration**: Week 2-3
**Goal**: Automated content scraping with change detection

### Tasks

#### 2.1 Web Scraper
- [ ] Configurable URL list management
- [ ] Respectful crawling (rate limiting, robots.txt)
- [ ] HTML to clean text conversion
- [ ] Language detection (EN/FR)
- [ ] Error handling and retry logic

```python
# src/scraper/crawler.py
import httpx
from bs4 import BeautifulSoup
import asyncio
from dataclasses import dataclass
from typing import AsyncGenerator

@dataclass
class ScrapedPage:
    url: str
    title: str
    content: str
    language: str
    html: str
    metadata: dict

class CanadaCrawler:
    def __init__(
        self,
        base_urls: list[str],
        rate_limit: float = 1.0,  # seconds between requests
    ):
        self.base_urls = base_urls
        self.rate_limit = rate_limit
        
    async def crawl(self) -> AsyncGenerator[ScrapedPage, None]:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "Canada.ca-ChatBot/1.0"}
        ) as client:
            for url in self.base_urls:
                try:
                    page = await self._fetch_and_parse(client, url)
                    yield page
                    await asyncio.sleep(self.rate_limit)
                except Exception as e:
                    # Log error, continue with next URL
                    pass
    
    async def _fetch_and_parse(
        self, 
        client: httpx.AsyncClient, 
        url: str
    ) -> ScrapedPage:
        response = await client.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract main content (canada.ca specific selectors)
        main_content = soup.select_one('main') or soup.select_one('article')
        title = soup.select_one('h1')
        
        # Detect language from HTML lang attribute or URL pattern
        language = self._detect_language(url, soup)
        
        return ScrapedPage(
            url=url,
            title=title.get_text(strip=True) if title else "",
            content=self._clean_text(main_content),
            language=language,
            html=response.text,
            metadata={
                "scraped_at": datetime.utcnow().isoformat(),
                "status_code": response.status_code,
            }
        )
```

#### 2.2 Content Chunking
- [ ] Semantic chunking strategy
- [ ] Overlap for context preservation
- [ ] Metadata preservation per chunk

```python
# src/scraper/chunker.py
from langchain.text_splitter import RecursiveCharacterTextSplitter

class ContentChunker:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
    
    def chunk_document(
        self, 
        content: str, 
        metadata: dict
    ) -> list[dict]:
        chunks = self.splitter.split_text(content)
        return [
            {
                "content": chunk,
                "chunk_index": i,
                "metadata": {**metadata, "chunk_index": i, "total_chunks": len(chunks)}
            }
            for i, chunk in enumerate(chunks)
        ]
```

#### 2.3 Change Detection
- [ ] Content hashing
- [ ] Diff detection
- [ ] Incremental updates only

```python
# src/scraper/change_detector.py
import hashlib

class ChangeDetector:
    def compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def has_changed(
        self, 
        url: str, 
        new_content: str,
        document_repo: DocumentRepository
    ) -> bool:
        existing = await document_repo.get_by_url(url)
        if not existing:
            return True  # New document
        
        new_hash = self.compute_hash(new_content)
        return existing.content_hash != new_hash
```

#### 2.4 Embedding Generation
- [ ] Batch embedding generation
- [ ] Rate limiting for API calls
- [ ] Error handling and retry

```python
# src/llm/embeddings/factory.py
from langchain_openai import AzureOpenAIEmbeddings
from src.config import settings

class EmbeddingFactory:
    @staticmethod
    def create_embeddings():
        if settings.llm_provider == "azure_openai":
            return AzureOpenAIEmbeddings(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                deployment=settings.azure_openai_embedding_deployment,
                api_version=settings.azure_openai_api_version,
            )
        # Add other providers...
```

#### 2.5 Vector Store Integration
- [ ] pgvector store operations
- [ ] Batch upsert
- [ ] Similarity search

```python
# src/vectorstore/pgvector.py
from langchain_community.vectorstores import PGVector

class VectorStore:
    def __init__(self, connection_string: str, embeddings):
        self.store = PGVector(
            connection_string=connection_string,
            embedding_function=embeddings,
            collection_name="document_chunks",
        )
    
    async def add_documents(self, documents: list[dict]):
        texts = [d["content"] for d in documents]
        metadatas = [d["metadata"] for d in documents]
        await self.store.aadd_texts(texts, metadatas)
    
    async def similarity_search(
        self, 
        query: str, 
        k: int = 5,
        filter: dict = None
    ) -> list:
        return await self.store.asimilarity_search(
            query, k=k, filter=filter
        )
```

#### 2.6 Ingestion Pipeline Orchestration
- [ ] Full pipeline orchestrator
- [ ] Progress tracking
- [ ] Error reporting

#### 2.7 Scheduled Job
- [ ] Azure Functions timer trigger (alternative: APScheduler)
- [ ] 2 AM nightly execution
- [ ] Alerting on failures

### Phase 2 Deliverables
- [ ] Working scraper for configurable URL list
- [ ] Content stored in PostgreSQL with embeddings
- [ ] Change detection working
- [ ] Manual trigger script for testing
- [ ] Job scheduler ready (local testing)

---

## Phase 3: Agent Intelligence

**Duration**: Week 3-4
**Goal**: Sophisticated conversational agent with citations

### Tasks

#### 3.1 Enhanced LangGraph Agent
- [ ] Multi-step reasoning
- [ ] Query routing (simple vs complex questions)
- [ ] Source citation in responses
- [ ] Conversation memory integration

```python
# src/agent/graph.py (enhanced)
from langgraph.graph import StateGraph, END
from src.agent.state import AgentState
from src.agent.nodes import router, retriever, generator, guardrails

def create_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("route", router.route_query)
    graph.add_node("retrieve", retriever.retrieve)
    graph.add_node("generate", generator.generate)
    graph.add_node("check_guardrails", guardrails.check)
    
    # Conditional routing
    graph.add_conditional_edges(
        "route",
        router.decide_path,
        {
            "simple": "generate",      # Direct answer
            "rag": "retrieve",          # Need retrieval
        }
    )
    
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "check_guardrails")
    graph.add_edge("check_guardrails", END)
    
    graph.set_entry_point("route")
    
    return graph.compile()
```

#### 3.2 Bilingual Support
- [ ] Language detection on input
- [ ] Language-specific system prompts
- [ ] Response in detected language
- [ ] Bilingual retrieval (search in both languages)

```python
# src/agent/nodes/language_detector.py
from langdetect import detect

def detect_language(text: str) -> str:
    """Detect if text is English or French."""
    try:
        lang = detect(text)
        return "fr" if lang == "fr" else "en"
    except:
        return "en"  # Default to English
```

```python
# src/agent/prompts/system_en.py
SYSTEM_PROMPT_EN = """You are a helpful assistant for Canada.ca, the official website of the Government of Canada.

Your role is to provide accurate, helpful information based on the official content from canada.ca.

Guidelines:
1. Always cite your sources with the exact URL when providing information
2. If you don't have information to answer a question, say so clearly
3. Be concise but thorough in your responses
4. If a question is outside the scope of canada.ca content, politely redirect
5. Never make up information - only use what's in the provided context

When citing sources, use this format:
[Source: Title of Page](URL)

Current conversation context:
{conversation_history}

Retrieved information:
{context}
"""
```

#### 3.3 Conversation Memory
- [ ] Session-based memory storage
- [ ] Context window management
- [ ] Memory summarization for long conversations

```python
# src/agent/memory.py
from langchain.memory import ConversationBufferWindowMemory
from src.db.repositories.session import SessionRepository

class SessionMemory:
    def __init__(
        self, 
        session_id: str,
        session_repo: SessionRepository,
        max_messages: int = 10
    ):
        self.session_id = session_id
        self.session_repo = session_repo
        self.max_messages = max_messages
    
    async def get_history(self) -> list[dict]:
        messages = await self.session_repo.get_messages(
            self.session_id, 
            limit=self.max_messages
        )
        return [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
    
    async def add_message(self, role: str, content: str, sources: list = None):
        await self.session_repo.add_message(
            session_id=self.session_id,
            role=role,
            content=content,
            sources=sources
        )
```

#### 3.4 Citation System
- [ ] Source attribution in responses
- [ ] Link back to original pages
- [ ] Confidence scoring

#### 3.5 Fallback Handling
- [ ] Graceful degradation when no relevant content
- [ ] Redirect to relevant canada.ca pages
- [ ] Clear "I don't know" responses

### Phase 3 Deliverables
- [ ] Agent responds in user's language
- [ ] Citations included in responses
- [ ] Conversation context maintained
- [ ] Quality responses for in-scope questions

---

## Phase 4: Security & Guardrails

**Duration**: Week 4-5
**Goal**: Secure, responsible AI system

### Tasks

#### 4.1 PII Detection & Redaction
- [ ] Microsoft Presidio integration
- [ ] Detect PII in user input
- [ ] Redact before processing/logging
- [ ] Alert on PII detection

```python
# src/security/pii_detector.py
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

class PIIDetector:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Canadian-specific entity types
        self.entities = [
            "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
            "CREDIT_CARD", "IBAN_CODE", "IP_ADDRESS",
            "SIN",  # Social Insurance Number (custom)
            "HEALTH_CARD",  # Provincial health cards (custom)
        ]
    
    def detect(self, text: str) -> list[dict]:
        results = self.analyzer.analyze(
            text=text,
            entities=self.entities,
            language="en"
        )
        return [
            {
                "entity_type": r.entity_type,
                "start": r.start,
                "end": r.end,
                "score": r.score
            }
            for r in results
        ]
    
    def anonymize(self, text: str) -> str:
        results = self.analyzer.analyze(text=text, entities=self.entities, language="en")
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized.text
```

#### 4.2 Input Validation
- [ ] Maximum input length
- [ ] Content type validation
- [ ] Malicious pattern detection

```python
# src/security/input_validator.py
from pydantic import BaseModel, validator
import re

class ChatInput(BaseModel):
    message: str
    session_id: str | None = None
    
    @validator('message')
    def validate_message(cls, v):
        # Length check
        if len(v) > 2000:
            raise ValueError("Message too long (max 2000 characters)")
        
        # Empty check
        if not v.strip():
            raise ValueError("Message cannot be empty")
            
        return v.strip()
```

#### 4.3 Prompt Injection Protection
- [ ] Input sanitization
- [ ] Instruction hierarchy enforcement
- [ ] Suspicious pattern detection

```python
# src/security/prompt_guard.py
import re

class PromptGuard:
    SUSPICIOUS_PATTERNS = [
        r"ignore\s+(previous|above|all)\s+instructions",
        r"disregard\s+(your|the)\s+instructions",
        r"you\s+are\s+now\s+",
        r"pretend\s+to\s+be",
        r"act\s+as\s+if",
        r"system\s*:\s*",
        r"<\s*system\s*>",
    ]
    
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_PATTERNS]
    
    def is_suspicious(self, text: str) -> tuple[bool, list[str]]:
        detected = []
        for pattern in self.patterns:
            if pattern.search(text):
                detected.append(pattern.pattern)
        return len(detected) > 0, detected
```

#### 4.4 Rate Limiting
- [ ] Per-IP rate limiting
- [ ] Per-session rate limiting
- [ ] Graceful handling of limit exceeded

```python
# src/api/middleware/rate_limiter.py
from fastapi import Request, HTTPException
import redis.asyncio as redis
from src.config import settings

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.limit = settings.rate_limit_requests
        self.window = settings.rate_limit_window_seconds
    
    async def check_rate_limit(self, key: str) -> bool:
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, self.window)
        return current <= self.limit
    
    async def __call__(self, request: Request):
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"
        
        if not await self.check_rate_limit(key):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
```

#### 4.5 Content Moderation (Output)
- [ ] Azure Content Safety integration
- [ ] Block harmful content in responses
- [ ] Log moderation events

```python
# src/security/content_moderator.py
from azure.ai.contentsafety import ContentSafetyClient
from azure.core.credentials import AzureKeyCredential

class ContentModerator:
    def __init__(self, endpoint: str, key: str):
        self.client = ContentSafetyClient(endpoint, AzureKeyCredential(key))
    
    async def is_safe(self, text: str) -> tuple[bool, dict]:
        # Analyze text for harmful content
        response = self.client.analyze_text({"text": text})
        
        # Check all categories
        categories = {
            "hate": response.hate_result.severity,
            "self_harm": response.self_harm_result.severity,
            "sexual": response.sexual_result.severity,
            "violence": response.violence_result.severity,
        }
        
        # Block if any category > threshold
        is_safe = all(severity < 2 for severity in categories.values())
        return is_safe, categories
```

#### 4.6 Audit Logging
- [ ] Log all interactions (with PII redacted)
- [ ] Security event logging
- [ ] Retention policy

#### 4.7 HTTPS Enforcement
- [ ] TLS 1.3 configuration
- [ ] Certificate management

### Phase 4 Deliverables
- [ ] PII detection working (no PII stored)
- [ ] Rate limiting active
- [ ] Prompt injection protection
- [ ] Content moderation on outputs
- [ ] Security audit log

### Security Checklist
- [ ] No PII in logs
- [ ] No PII in vector store
- [ ] Rate limiting on all endpoints
- [ ] Input validation on all endpoints
- [ ] Prompt injection protection
- [ ] Content moderation
- [ ] HTTPS only
- [ ] Secrets in Key Vault
- [ ] Audit trail

---

## Phase 5: Production Hardening

**Duration**: Week 5-6
**Goal**: Production-ready, observable system

### Tasks

#### 5.1 Comprehensive Logging
- [ ] Structured JSON logging
- [ ] Request/response logging
- [ ] LLM call logging (via LangSmith)
- [ ] Error tracking

```python
# src/config/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, 'request_id'):
            log_obj["request_id"] = record.request_id
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    logger = logging.getLogger("canadaca")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    return logger
```

#### 5.2 Error Handling
- [ ] Global exception handler
- [ ] Graceful error responses
- [ ] Retry logic for external services
- [ ] Circuit breaker pattern

```python
# src/api/middleware/error_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("canadaca")

async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Unhandled exception: {exc}",
        extra={"request_id": request_id},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected error occurred",
            "request_id": request_id,
            "detail": "Please try again later"
        }
    )
```

#### 5.3 Caching Layer
- [ ] Response caching for common queries
- [ ] Cache invalidation strategy
- [ ] Cache warming

```python
# src/cache/redis_cache.py
import redis.asyncio as redis
import json
from typing import Any
import hashlib

class ResponseCache:
    def __init__(self, redis_client: redis.Redis, ttl: int = 3600):
        self.redis = redis_client
        self.ttl = ttl
    
    def _make_key(self, query: str, context: dict) -> str:
        content = f"{query}:{json.dumps(context, sort_keys=True)}"
        return f"cache:{hashlib.md5(content.encode()).hexdigest()}"
    
    async def get(self, query: str, context: dict = {}) -> Any | None:
        key = self._make_key(query, context)
        cached = await self.redis.get(key)
        return json.loads(cached) if cached else None
    
    async def set(self, query: str, response: Any, context: dict = {}):
        key = self._make_key(query, context)
        await self.redis.setex(key, self.ttl, json.dumps(response))
```

#### 5.4 Health Checks
- [ ] Liveness probe
- [ ] Readiness probe
- [ ] Dependency health checks

```python
# src/api/routes/health.py
from fastapi import APIRouter, Depends
from src.db.connection import get_db
from src.cache.redis_cache import get_redis

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "healthy"}

@router.get("/ready")
async def ready(db = Depends(get_db), redis = Depends(get_redis)):
    checks = {}
    
    # Check database
    try:
        await db.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"
    
    # Check Redis
    try:
        await redis.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {e}"
    
    all_healthy = all(v == "healthy" for v in checks.values())
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks
    }
```

#### 5.5 Load Testing
- [ ] Locust test scenarios
- [ ] Performance benchmarks
- [ ] Identify bottlenecks

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class ChatUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def chat(self):
        self.client.post(
            "/api/v1/chat",
            json={
                "message": "How do I apply for a passport?",
                "session_id": None
            }
        )
    
    @task(3)
    def health_check(self):
        self.client.get("/health")
```

#### 5.6 CI/CD Pipeline
- [ ] GitHub Actions workflow
- [ ] Linting and type checking
- [ ] Unit and integration tests
- [ ] Docker build and push
- [ ] Deployment automation

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install ruff mypy
      - run: ruff check src/
      - run: mypy src/

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: ankane/pgvector:latest
        env:
          POSTGRES_DB: test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/ --cov=src

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: canadaca-api:${{ github.sha }}
```

### Phase 5 Deliverables
- [ ] Structured logging throughout
- [ ] Error handling complete
- [ ] Caching layer working
- [ ] CI pipeline passing
- [ ] Load test results documented

---

## Phase 6: Cloud Deployment

**Duration**: Week 6-7
**Goal**: Production deployment on Azure

### Tasks

#### 6.1 Infrastructure as Code (Terraform)
- [ ] Resource group
- [ ] Container Apps environment
- [ ] PostgreSQL Flexible Server
- [ ] Redis Cache
- [ ] Key Vault
- [ ] Container Registry
- [ ] Application Insights

```hcl
# infrastructure/terraform/main.tf
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "main" {
  name     = "rg-canadaca-${var.environment}"
  location = "Canada Central"
}

resource "azurerm_container_app_environment" "main" {
  name                = "cae-canadaca-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                = "psql-canadaca-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  
  sku_name   = "B_Standard_B1ms"  # Burstable, cost-effective
  storage_mb = 32768
  version    = "15"
  
  administrator_login    = var.db_admin_user
  administrator_password = var.db_admin_password
}

# Enable pgvector extension
resource "azurerm_postgresql_flexible_server_configuration" "pgvector" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "VECTOR"
}
```

#### 6.2 Container Registry Setup
- [ ] Azure Container Registry
- [ ] Service principal for CI/CD

#### 6.3 Container Apps Deployment
- [ ] API container app
- [ ] Scraper container job (scheduled)
- [ ] Auto-scaling rules
- [ ] Environment variables from Key Vault

```hcl
resource "azurerm_container_app" "api" {
  name                         = "ca-canadaca-api-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    container {
      name   = "api"
      image  = "${azurerm_container_registry.main.login_server}/canadaca-api:latest"
      cpu    = 0.5
      memory = "1Gi"
      
      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-key"
      }
    }
    
    min_replicas = 1
    max_replicas = 10
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
  
  scale {
    min_replicas = 1
    max_replicas = 10
    
    rules {
      name = "http-scaling"
      http {
        metadata = {
          concurrentRequests = "10"
        }
      }
    }
  }
}
```

#### 6.4 Secrets Management
- [ ] Key Vault setup
- [ ] Managed identity
- [ ] Secret references in Container Apps

#### 6.5 Monitoring & Alerting
- [ ] Application Insights integration
- [ ] Custom dashboards
- [ ] Alert rules for errors, latency

#### 6.6 Static Frontend Deployment
- [ ] Azure Static Web Apps or CDN
- [ ] Custom domain (optional)

### Phase 6 Deliverables
- [ ] Terraform code complete
- [ ] Staging environment deployed
- [ ] Production environment deployed
- [ ] Monitoring dashboards live
- [ ] Alert rules configured

---

## Phase 7: Analytics & Iteration

**Duration**: Ongoing
**Goal**: Continuous improvement based on usage

### Tasks

#### 7.1 Usage Analytics
- [ ] Query volume tracking
- [ ] Response quality metrics
- [ ] Language distribution
- [ ] Popular topics

#### 7.2 Feedback Collection
- [ ] Thumbs up/down on responses
- [ ] Feedback storage
- [ ] Quality improvement loop

#### 7.3 A/B Testing Infrastructure
- [ ] Feature flags
- [ ] Experiment tracking
- [ ] Statistical analysis

#### 7.4 Content Expansion
- [ ] Add more canada.ca sections
- [ ] Improve content coverage
- [ ] Iterative prompt tuning

---

## Cost Estimation

### Monthly Costs (Initial 100 queries/day)

| Service | SKU | Est. Monthly Cost (CAD) |
|---------|-----|-------------------------|
| Azure OpenAI (GPT-4o) | Pay-as-you-go | ~$50-100 |
| Azure OpenAI (Embeddings) | Pay-as-you-go | ~$10-20 |
| PostgreSQL Flexible | B_Standard_B1ms | ~$35 |
| Azure Cache for Redis | Basic C0 | ~$20 |
| Container Apps | Consumption | ~$20-50 |
| Application Insights | Pay-as-you-go | ~$10 |
| Container Registry | Basic | ~$7 |
| **Total** | | **~$150-250/month** |

### Scaling Notes
- Costs scale primarily with LLM usage
- Container Apps auto-scales to zero when not in use
- PostgreSQL can be scaled up if needed

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM API outage | High | Multi-provider fallback, graceful degradation |
| Cost overrun | Medium | Rate limiting, caching, usage alerts |
| Content accuracy | High | Citation system, user feedback, regular review |
| PII exposure | High | Presidio detection, no PII logging, audit |
| Prompt injection | Medium | Input validation, pattern detection, sandboxing |
| canada.ca changes | Medium | Change detection, monitoring, adaptive scraping |

---

## Next Steps

1. **Confirm** this plan meets requirements
2. **Create** initial project structure (Phase 1.1)
3. **Set up** local development environment
4. **Begin** Phase 1 implementation

---

*Document Version: 1.0*
*Last Updated: January 31, 2026*
