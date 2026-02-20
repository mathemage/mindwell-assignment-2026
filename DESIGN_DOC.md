# Mindwell AI — Clinical Supervisor: Design Document

> **Role**: AI Engineer / Architect · **Context**: Regulated Health-Tech Environment  
> **Diagram**: [`diagrams/system_architecture.drawio`](diagrams/system_architecture.drawio) (open in [app.diagrams.net](https://app.diagrams.net/))

---

## System Diagram Overview

The Draw.io file at `diagrams/system_architecture.drawio` shows the full end-to-end flow
across four vertical lanes:

| Lane | Colour | Responsibility |
|------|--------|----------------|
| API Gateway & Auth | Blue | FastAPI, JWT/RBAC, PII Redaction |
| Agent Orchestrator | Red | Sequential multi-agent pipeline |
| Data & Memory | Purple | PostgreSQL + pgvector, CBT Knowledge Base |
| LLM & Observability | Yellow | Self-hosted LLM, structlog, OpenTelemetry/Jaeger, Drift Monitor |

Actors outside the main pipeline: **Patient** (submits journal/homework) and **Therapist**
(reviews and approves the AI-drafted clinical response).

---

## A. System Architecture & Stack

### End-to-End Flow

```
Patient submits journal entry
        │
        ▼
┌─────────────────────────────┐
│  FastAPI — /chat endpoint   │
│  JWT auth + RBAC            │  ← All traffic stays inside VPC
│  PII Redactor               │    (email/phone/SSN → [REDACTED])
└──────────────┬──────────────┘
               │ sanitised message
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  AgentOrchestrator  (sequential pipeline with per-step timeouts)    │
│                                                                     │
│  1. SafetyAgent — INPUT                                             │
│     ├─ Crisis keywords → return emergency resources (escalate)      │
│     ├─ Medical advice request → return disclaimer (refuse)          │
│     └─ OK → continue                                                │
│                                                                     │
│  2. RetrieverAgent                                                  │
│     └─ Embed query → cosine-similarity search → top-k CBT chunks   │
│                                                                     │
│  3. DraftAgent                                                      │
│     └─ Build context window → LLM call → extract citations         │
│                                                                     │
│  4. SafetyAgent — OUTPUT                                            │
│     └─ Groundedness check → length check → refuse if unsupported   │
│                                                                     │
│  5. FinalizerAgent                                                  │
│     └─ Compose final draft + citations                              │
└──────────────┬──────────────────────────────────────────────────────┘
               │ draft response
               ▼
┌─────────────────────────────┐
│  Therapist Review UI        │
│  (draft → Approve / Edit)   │
└─────────────────────────────┘
               │ approved response
               ▼
          Patient
```

### Orchestration Design

The pipeline is implemented as a **sequential state machine** (see
`backend/app/agents/orchestrator.py`). Each agent is a pure, testable function.
Timeouts are enforced with `asyncio.wait_for` so a slow LLM call never hangs the
whole request.

Although the current implementation uses a hand-rolled sequential pipeline, the
design maps directly to **LangGraph** concepts:

| LangGraph concept | This implementation |
|---|---|
| `StateGraph` node | Agent class with typed input/output |
| `conditional_edges` | Safety check branches (crisis / medical / ok) |
| `checkpointer` | SQLAlchemy `Conversation` + `Message` models |
| `interrupt_before` | Therapist review step before final delivery |

LangGraph is the preferred orchestrator for future iterations because it provides
built-in state persistence, visual debugging, and native `human-in-the-loop`
pause/resume — exactly what the therapist approval workflow requires.
The current pure-Python approach was chosen for minimal dependencies in the MVP.

### Memory Store

**Choice: PostgreSQL 16 + pgvector extension** (self-hosted via Docker)

| Criterion | Rationale |
|---|---|
| **Self-hostable** | Runs in any VPC on commodity compute; no SaaS required |
| **Vector search** | pgvector extension provides cosine-similarity search; no separate Qdrant/Pinecone needed |
| **Budget** | Open-source (MIT / BSD); zero licence cost |
| **ACID compliance** | Transactional writes; no possibility of partial memory corruption |
| **Relational data** | Users, conversations, and embeddings in one engine simplifies ops |
| **Audit trail** | Native row-level timestamping; no extra infrastructure for compliance logs |

Patient facts are stored as **rows in the `Embedding` table** keyed by
`user_id` (pseudonymised UUID). A similarity query over that user's rows
retrieves relevant memories from *any* past session — giving the system
long-term memory without a separate memory microservice.

### Persistence: Crash-Safe Strategy

PostgreSQL's **Write-Ahead Log (WAL)** guarantees zero data loss on container
crash: every `INSERT`/`UPDATE` is flushed to the WAL before the call returns.
The named Docker volume (`postgres_data`) maps the WAL and data directory to the
host filesystem, so data survives container restarts.

For production, add:

1. **Continuous archiving** — stream WAL segments to S3/GCS (encrypted at rest).
2. **Daily `pg_dump`** — compressed, encrypted logical backup to object storage.
3. **Point-in-Time Recovery (PITR)** — restore to any second using WAL replay.

---

## B. Data Privacy & Observability

### PII Before the Context Window

Patient text is scrubbed of personally identifiable information *before* it
enters the LLM context window:

```
Raw message → PII Redactor (regex patterns) → sanitised_message
              email      → [EMAIL]
              phone      → [PHONE]
              SSN        → [SSN]
              credit card→ [CREDIT_CARD]
```

The redaction happens in the API layer (`backend/app/core/security.py`) — the
LLM never receives raw PII even if the patient accidentally includes it.
Pseudonymised `user_id`s (not email addresses) are passed as context so the
model can reference "this patient" without knowing their identity.

### Self-Hosted Tracing

**Stack: OpenTelemetry SDK (Python) → self-hosted Jaeger**

All agents emit OpenTelemetry spans. Jaeger runs as a sidecar container inside
the VPC — zero telemetry leaves the network boundary.

Debugging a hallucination session:

1. Retrieve the trace by `session_id` in Jaeger UI.
2. Inspect the `RetrieverAgent` span: which chunks were returned, what similarity
   scores were assigned.
3. Inspect the `DraftAgent` span: exact prompt sent to the LLM (sanitised),
   token counts, raw completion.
4. Inspect `SafetyAgent` output span: why groundedness check passed or failed.

Complementing this, **structlog** writes structured JSON logs with the
`sanitize_event_dict` processor, which automatically redacts any field matching
PII patterns — safe to ship to a log aggregator (e.g., self-hosted Loki).

### Drift Monitoring

Model tone can drift away from CBT protocols as the underlying LLM is updated
or fine-tuned. The monitoring strategy is:

1. **Offline benchmark eval** (`backend/app/eval/`) — a curated dataset of
   CBT questions with labelled ground-truth responses. Run nightly in CI;
   alert if hit@3 retrieval or safety accuracy drops more than 5 percentage
   points from the baseline.
2. **Response-level CBT compliance scorer** — a lightweight LLM-as-judge prompt
   that rates each response on a rubric (uses Socratic questioning? avoids
   unsolicited diagnosis? recommends professional care when appropriate?).
   Aggregate the daily mean; alert on regression.
3. **Embedding-space drift** — periodically compute the centroid of recent
   responses and measure cosine distance from a "golden" CBT response corpus.
   Significant drift triggers a review.

---

## C. Security & Isolation

### Tenant Isolation: Patient A ↔ Patient B

Every query that touches patient data is scoped by `user_id`:

```python
# RetrieverAgent — simplified example
db.query(Embedding).filter(
    Embedding.chunk.has(Chunk.document.has(Document.owner_id == user.id))
)
```

A patient can never retrieve another patient's memories or conversations because:

- **Pseudonymised IDs** — no real identity information leaks even in logs.
- **Row-level scoping** — all ORM queries carry the `user_id` filter; the ORM
  layer prevents raw SQL injection via parameterised queries.
- **RBAC** — the `get_current_user` dependency ensures the JWT `sub` matches the
  `user_id` being queried.
- **(Future)** PostgreSQL **Row-Level Security (RLS)** policies can enforce
  isolation at the database engine level as an additional defence-in-depth layer.

### VPC Security: Agent Container ↔ Database Container

```
┌──────────────────────── Private VPC Subnet ──────────────────────────┐
│                                                                       │
│  ┌─────────────────┐    TLS 1.3 (mTLS)    ┌──────────────────────┐  │
│  │  Backend Pod    │ ──────────────────── │  PostgreSQL Pod      │  │
│  │  (FastAPI)      │    port 5432          │  (pgvector)          │  │
│  └─────────────────┘                      └──────────────────────┘  │
│          │                                         │                  │
│   No public IP                             No public IP               │
│   Security Group: allow 8000 inbound      Security Group: allow 5432 │
│   only from API Gateway/ALB               only from Backend SG        │
└───────────────────────────────────────────────────────────────────────┘
```

- **Secrets** stored in AWS Secrets Manager / HashiCorp Vault; injected as
  environment variables at runtime — never committed to source control.
- **Database credentials** rotated automatically using Vault's PostgreSQL
  dynamic secrets.
- **Network policy** (Kubernetes `NetworkPolicy` or AWS Security Groups): the
  database port is reachable *only* from the backend pod — not from the internet,
  not from any other service.
- **Encryption at rest**: managed PostgreSQL (e.g., AWS RDS) enables AES-256
  disk encryption by default.

---

## D. User Experience (Thought Process)

### Latency Trade-off: Intelligence vs. Speed

The pipeline has three main latency contributors:

| Step | Typical latency | Mitigation |
|---|---|---|
| Input safety check | ~5 ms | Rule-based (no LLM call) |
| Vector retrieval | 50–300 ms | pgvector index (HNSW) |
| LLM generation | 1–5 s | Streaming SSE; show partial text |
| Output safety + finalize | ~10 ms | Rule-based |

The safety checks are intentionally rule-based (not LLM-based) so they add
near-zero latency. The LLM call dominates; the solution is **response streaming**
via Server-Sent Events: the therapist sees the draft text appearing word-by-word
rather than waiting for the full response.

### Handling a 3-Second Memory Retrieval

If memory retrieval takes 3 seconds (e.g., cold PostgreSQL on a small instance):

1. **Optimistic UI** — immediately display a typing indicator / skeleton card in
   the therapist UI to signal the system is working.
2. **HNSW index** on the `embedding` column (`CREATE INDEX … USING hnsw`) reduces
   retrieval to O(log n) even for millions of vectors; typically < 100 ms.
3. **Session-scoped cache** — after the first retrieval for a session, cache the
   top-k chunks in application memory for the duration of the conversation
   (Redis or `lru_cache`). Subsequent turns in the same session skip the DB call.
4. **Async pipeline** — retrieval and the start of the LLM context-build happen
   concurrently: `asyncio.gather(retrieve(), build_system_prompt())`.

---

## E. Strategic Thinking

### Top 3 Questions Before Writing a Single Line of Code

1. **What is the therapist's review workflow?**
   Does the therapist see the draft inline (like a Gmail smart-reply they can
   edit) or in a separate review queue? The answer determines whether the system
   is synchronous (patient waits) or asynchronous (draft queued for batch review),
   which changes the entire latency story and UX.

2. **Which specific CBT protocols and frameworks must the AI follow?**
   CBT is not monolithic — Beck's cognitive model, DBT, ACT, and behavioural
   activation all have distinct language norms. Without a canonical protocol list,
   the knowledge base and the drift monitor cannot be properly calibrated. This
   also determines what the CBT Knowledge Base must contain.

3. **What are the data retention and regulatory requirements for patient records?**
   Are these sessions considered Protected Health Information (PHI) under HIPAA?
   Do we need to operate under GDPR (EU patients)? The answers determine whether
   we need Business Associate Agreements, explicit consent flows, right-to-erasure
   pipelines, and how long we can legally retain conversation history — all of
   which directly affect the memory store design.

### The "AI-First" Pivot: Removing the Therapist from the Loop

**How the architecture changes for fully autonomous AI therapy:**

| Component | Human-in-the-Loop (current) | Autonomous (pivot) |
|---|---|---|
| FinalizerAgent | Produces *draft* for therapist | Delivers response *directly* to patient |
| SafetyAgent | Rule-based (fast, conservative) | LLM-based + clinical classifier with higher confidence threshold |
| Escalation | Alert therapist | Alert on-call crisis counsellor + emergency services integration |
| Audit trail | Conversation logs | Mandatory; every decision must be explainable and reproducible |
| Feedback loop | Therapist edits = implicit signal | RLHF pipeline: patient-reported outcomes, therapist retrospective ratings |

**What I would have built differently from Day 1:**

1. **Confidence scoring on every agent output** — currently the pipeline returns
   a response or refuses. For autonomous therapy, every output needs a calibrated
   confidence score so the system can self-escalate when uncertain (e.g.,
   "I'm not confident enough in this response — routing to standby counsellor").

2. **Richer patient state model** — the current memory store is flat (embeddings
   of messages). An autonomous system needs a structured patient profile: tracked
   CBT homework completion, identified cognitive distortions, progress on
   behavioural experiments. This is a semantic memory layer on top of the
   episodic embedding store.

3. **Explainability layer** — therapists (and regulators) need to understand *why*
   the AI said what it said. I would have built a citation-to-protocol mapping
   from Day 1: every sentence in the response traces to a specific CBT principle
   and the retrieved knowledge base passage that supports it.

4. **Stricter input/output contracts** — autonomous therapy requires typed,
   validated agent I/O (e.g., Pydantic models for each agent's state) from the
   start, not just free-text strings, so that safety constraints are enforced at
   the type level.

---

## Technology Summary

| Component | Choice | Rationale |
|---|---|---|
| Orchestration | LangGraph (current: hand-rolled sequential) | Native HITL pause/resume, visual debugging, open-source |
| LLM | OpenAI-compatible interface; Ollama/vLLM self-hosted | Vendor-neutral; stays inside VPC |
| Vector + relational DB | PostgreSQL 16 + pgvector | Self-hostable, ACID, zero extra licence cost |
| Embeddings | OpenAI `text-embedding-3-small` (or local model) | 1536-dim; pluggable via abstract interface |
| Tracing | OpenTelemetry → self-hosted Jaeger | No SaaS telemetry; full session replay |
| Logging | structlog + JSON + `sanitize_event_dict` | PII-safe by default; pairs with Loki/Grafana |
| Infra | Docker Compose (dev) → Kubernetes (prod) | Portable; no proprietary cloud dependencies |
| Secrets | HashiCorp Vault / AWS Secrets Manager | Rotation, audit, zero secrets in code |

---

*Document version: 1.0 — 2026-02-20*  
*See also: [ARCHITECTURE.md](ARCHITECTURE.md), [SECURITY.md](SECURITY.md), [DATA_PRIVACY.md](DATA_PRIVACY.md)*
