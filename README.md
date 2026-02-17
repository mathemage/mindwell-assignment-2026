# Mindwell AI - CBT Assistant

Production-ready MVP for an AI-powered cognitive behavioral therapy (CBT) assistant with RAG, safety guardrails, and evaluation.

## Features

- 🤖 **AI Chat Assistant**: Answers questions grounded in approved knowledge base with citations
- 🔒 **Safety Guardrails**: Crisis detection, medical advice boundaries, and PII redaction
- 📚 **Knowledge Base**: Upload and manage CBT documents (Markdown, PDF, text)
- 🔍 **RAG Pipeline**: Multi-agent system (retrieve → draft → safety-check → final)
- 📊 **Evaluation**: Offline evaluation for retrieval quality and safety
- 🔐 **Privacy-First**: Pseudonymization, PII redaction, no secrets logged
- 🧪 **Tested**: Unit tests, integration tests, type checking

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2
- **Database**: PostgreSQL with pgvector extension
- **LLM**: OpenAI-compatible API (configurable)
- **Dev Tools**: ruff, mypy, pytest, pre-commit
- **Infrastructure**: Docker Compose, GitHub Actions CI

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- OpenAI API key (or compatible endpoint)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd mindwell-assignment-2026
cp backend/.env.example backend/.env
```

### 2. Configure Environment

Edit `backend/.env` and set your OpenAI API key:

```bash
OPENAI_API_KEY=your-api-key-here
```

### 3. Start Services with Docker

```bash
docker-compose up -d
```

This starts:
- PostgreSQL with pgvector (port 5432)
- Backend API (port 8000)

### 4. Seed Database (Optional)

```bash
make seed
```

This ingests sample CBT documents from `data/sample_docs/`.

### 5. Test the API

Visit http://localhost:8000/docs for interactive API documentation.

## Development

### Local Development (Without Docker)

```bash
# Install dependencies
make install

# Run database with Docker
docker-compose up -d postgres

# Run backend locally
make dev
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Type check
make typecheck

# Run tests
make test
```

## API Usage

### 1. Login (Dev Mode)

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@admin.com"}'
```

### 2. Send Chat Message

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is CBT?"}'
```

## Security & Privacy

See [SECURITY.md](SECURITY.md) and [DATA_PRIVACY.md](DATA_PRIVACY.md) for details.

## Disclaimer

This is an AI assistant for educational purposes. It is NOT a replacement for professional mental health care.

If you're in crisis:
- Call 988 (Suicide & Crisis Lifeline)
- Text HOME to 741741 (Crisis Text Line)
- Call 911 or go to nearest emergency room
