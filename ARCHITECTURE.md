# Architecture

## Overview

Mindwell is a production-ready AI assistant for cognitive behavioral therapy (CBT) education, built with safety, privacy, and evaluation as core principles.

## System Components

### 1. API Layer (FastAPI)

**Routes**:
- `/auth/*` - Authentication (dev login with JWT)
- `/chat` - Chat endpoint with safety checks
- `/admin/docs/*` - Document management (admin only)
- `/health` - Health check

**Key Design Decisions**:
- FastAPI for async support and automatic OpenAPI docs
- JWT-based authentication (simplified for MVP)
- Role-based access control (RBAC) for admin endpoints
- Structured error responses

### 2. Database (PostgreSQL + pgvector)

**Models**:
- `User` - User accounts with pseudonymization
- `Document` - Knowledge base documents
- `Chunk` - Text chunks from documents
- `Embedding` - Vector embeddings (1536-dim for OpenAI)
- `Conversation` - Chat conversations
- `Message` - Individual messages
- `SafetyCheck` - Safety check records

**Key Design Decisions**:
- pgvector for semantic search (avoids separate vector DB)
- Pseudonymization of user IDs from creation
- Cascade deletes for data consistency
- Metadata as JSON for flexibility

### 3. RAG Pipeline

**Components**:
- **Chunker**: Splits documents by headings (markdown) or size
- **Embedding Service**: Generates vectors via LLM provider
- **Retrieval Service**: Cosine similarity search
- **Citation Builder**: Extracts document + section info

**Key Design Decisions**:
- Markdown-aware chunking preserves structure
- Configurable chunk size/overlap
- Top-k retrieval with similarity scores
- Citations include document title, section, and snippet

### 4. Multi-Agent System

**Agents**:
1. **RetrieverAgent**: Fetches relevant chunks
2. **DraftAgent**: Generates response with citations
3. **SafetyAgent**: Checks input and output
4. **FinalizerAgent**: Produces final response

**Orchestrator**:
- Sequential pipeline with timeouts
- Graceful degradation on failures
- Comprehensive logging at each step

**Key Design Decisions**:
- Agents as pure functions for testability
- Safety checks before and after generation
- Fallback responses for edge cases
- Timeout handling to prevent hangs

### 5. Safety System

**Policy Module**:
- Crisis keywords (suicide, self-harm)
- Medical advice detection (diagnosis, prescription)
- Emergency resources (hotlines, disclaimers)

**Classifier**:
- Rule-based for reliability
- Three outcomes: ok, refused, escalated
- Confidence scoring
- Response grounding verification

**Key Design Decisions**:
- Rule-based over ML for predictability
- Conservative thresholds (false positives acceptable)
- Logs all safety decisions with reasons
- Groundedness check prevents hallucinations

### 6. LLM Integration

**Provider Interface**:
- Abstract base class for portability
- Methods: `generate_embedding`, `chat_completion`

**OpenAI Implementation**:
- Async client for performance
- Configurable models and base URL
- Token usage tracking
- Error handling with retries

**Key Design Decisions**:
- Pluggable interface for provider flexibility
- OpenAI-compatible by default
- No hardcoded API keys (env vars only)
- Structured responses where possible

### 7. Privacy & Security

**PII Protection**:
- Regex-based detection (email, phone, SSN, credit card)
- Automatic redaction in logs and storage
- User pseudonymization

**Secrets Management**:
- Environment variables only
- Redaction in structured logs
- No secrets in error messages

**Key Design Decisions**:
- Privacy-by-default architecture
- Multiple layers of PII protection
- Audit trail for safety decisions
- Minimal data retention

### 8. Evaluation

**Metrics**:
- Retrieval: hit@1, hit@3, hit@5
- Safety: accuracy, false positive/negative rates
- Latency: p50, p95, p99

**Datasets**:
- Labeled queries for retrieval
- Safety test cases
- Regression test suite

**Key Design Decisions**:
- Offline evaluation for reproducibility
- Version-controlled test cases
- Automated in CI (when extended)

## Data Flow

### Chat Request Flow

```
1. User sends message → API endpoint
2. JWT authentication
3. SafetyAgent checks input
   ├─ Crisis detected → Return emergency resources
   ├─ Medical advice → Return disclaimer
   └─ OK → Continue
4. RetrieverAgent searches knowledge base
   └─ Embed query → Similarity search → Top-k chunks
5. DraftAgent generates response
   └─ Build context → LLM call → Extract citations
6. SafetyAgent checks output
   └─ Verify groundedness → Check length
7. FinalizerAgent produces final response
8. Store message with safety check
9. Return to user
```

### Document Ingestion Flow

```
1. Admin uploads file → API endpoint
2. Admin authentication
3. Extract text (markdown/PDF/plain)
4. Chunk text (by heading or size)
5. Generate embeddings (batch)
6. Store in database
   ├─ Document record
   ├─ Chunk records
   └─ Embedding records
7. Return document ID
```

## Tradeoffs

### Simplicity vs. Features

**Choice**: Start simple, extend as needed
- Rule-based safety (vs. ML classifier)
- SQLite-compatible models (vs. specialized schemas)
- Single embedding model (vs. ensemble)

**Rationale**: Easier to understand, test, and deploy. Can add complexity when justified by data.

### Performance vs. Safety

**Choice**: Prioritize safety
- Multiple safety checks add latency
- Conservative thresholds cause false positives
- Response grounding limits creativity

**Rationale**: In clinical domain, false negatives (missing crisis) are unacceptable. Latency and false positives are manageable.

### Flexibility vs. Constraints

**Choice**: Constrained but pluggable
- OpenAI-compatible LLM interface
- PostgreSQL with pgvector
- Structured logging format

**Rationale**: Constraints reduce complexity and bugs. Interfaces enable swapping components.

### Privacy vs. Functionality

**Choice**: Privacy-first
- Pseudonymization from start
- PII redaction even in logs
- No user content in error messages

**Rationale**: Trust is critical in mental health domain. Over-redaction is safer than under-redaction.

## Scalability Considerations

**Current Architecture** (MVP):
- Single backend instance
- Postgres on single node
- Synchronous embedding generation

**Future Improvements**:
- Horizontal scaling with load balancer
- Read replicas for queries
- Background job queue for embeddings
- Caching layer for common queries
- Distributed tracing

## Testing Strategy

**Unit Tests**:
- Pure functions (chunking, safety rules)
- Mock external dependencies (LLM, DB)

**Integration Tests**:
- In-memory SQLite database
- End-to-end agent pipeline
- API endpoints

**Evaluation**:
- Labeled datasets
- Regression tests for safety
- Performance benchmarks

## Monitoring & Observability

**Structured Logging**:
- JSON format in production
- Human-readable in development
- Automatic PII redaction

**Metrics** (Future):
- Request count, latency, errors
- Safety check outcomes
- LLM token usage, cost
- Retrieval quality (hit rate)

**Tracing** (Future):
- OpenTelemetry-ready hooks
- Distributed tracing for debugging
- Performance profiling

## Deployment

**MVP Deployment**:
```
Docker Compose:
├─ Postgres with pgvector
└─ FastAPI backend
```

**Production Deployment** (Recommended):
```
Kubernetes:
├─ Backend pods (2+ replicas)
├─ Managed PostgreSQL
├─ Secrets from vault
├─ Ingress with TLS
└─ Background workers
```

## Future Enhancements

1. **User Feedback Loop**: Thumbs up/down on responses
2. **Advanced Safety**: ML-based crisis detection
3. **Multi-turn Context**: Conversation history in prompts
4. **A/B Testing**: Compare prompt variations
5. **Admin Dashboard**: Analytics and monitoring UI
6. **Rate Limiting**: Prevent abuse
7. **Audit Logs**: Compliance and debugging
8. **Multi-language**: I18n support

## References

- FastAPI: https://fastapi.tiangolo.com/
- pgvector: https://github.com/pgvector/pgvector
- OpenAI API: https://platform.openai.com/docs
- Pydantic: https://docs.pydantic.dev/
- SQLAlchemy: https://www.sqlalchemy.org/
