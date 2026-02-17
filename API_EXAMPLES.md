# API Examples with cURL

This file contains example API calls using curl for testing the Mindwell AI API.

## Setup

Export your token as an environment variable after logging in:

```bash
export TOKEN="your-access-token-here"
export API_URL="http://localhost:8000"
```

## Authentication

### Login (Dev Mode)

```bash
# Login as regular user
curl -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'

# Login as admin
curl -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@admin.com"}'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### Get Current User

```bash
curl -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

## Chat

### Send a Message

```bash
curl -X POST "$API_URL/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is cognitive behavioral therapy?"
  }'
```

Response:
```json
{
  "conversation_id": "abc123...",
  "message": {
    "id": "msg456...",
    "content": "Cognitive Behavioral Therapy (CBT) is...",
    "citations": [
      {
        "document_id": "doc789...",
        "document_title": "Intro To Cbt",
        "section_heading": "What is CBT?",
        "chunk_index": 0,
        "text_snippet": "Cognitive Behavioral Therapy (CBT) is a structured..."
      }
    ],
    "safety_outcome": "ok"
  }
}
```

### Continue Conversation

```bash
curl -X POST "$API_URL/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can you tell me more about thought records?",
    "conversation_id": "abc123..."
  }'
```

### Test Safety Guardrails

#### Crisis Detection
```bash
curl -X POST "$API_URL/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I am feeling suicidal"
  }'
```

Expected: Safety escalation with emergency resources

#### Medical Advice Boundary
```bash
curl -X POST "$API_URL/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can you diagnose me with depression?"
  }'
```

Expected: Refused with medical disclaimer

### List Conversations

```bash
curl -X GET "$API_URL/chat/conversations" \
  -H "Authorization: Bearer $TOKEN"
```

### Get Conversation History

```bash
curl -X GET "$API_URL/chat/conversations/{conversation_id}/messages" \
  -H "Authorization: Bearer $TOKEN"
```

## Admin - Document Management

### Upload Document

```bash
# Upload a markdown file
curl -X POST "$API_URL/admin/docs/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/document.md"

# Upload a PDF
curl -X POST "$API_URL/admin/docs/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/document.pdf"
```

Response:
```json
{
  "id": "doc123...",
  "title": "document.md",
  "source_type": "markdown",
  "chunk_count": 15,
  "created_at": "2026-02-17T18:30:00"
}
```

### List Documents

```bash
curl -X GET "$API_URL/admin/docs?limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

### Get Document Details

```bash
curl -X GET "$API_URL/admin/docs/{document_id}" \
  -H "Authorization: Bearer $TOKEN"
```

### Re-index Document

```bash
curl -X POST "$API_URL/admin/docs/{document_id}/reindex" \
  -H "Authorization: Bearer $TOKEN"
```

## Health Check

```bash
curl -X GET "$API_URL/health"
```

## Complete Example Workflow

```bash
#!/bin/bash

API_URL="http://localhost:8000"

# 1. Login as admin
echo "Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@admin.com"}')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
echo "Token: $TOKEN"

# 2. Upload a document
echo "Uploading document..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/admin/docs/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@data/sample_docs/01_intro_to_cbt.md")

echo "Upload response: $UPLOAD_RESPONSE"

# 3. Send a chat message
echo "Sending chat message..."
CHAT_RESPONSE=$(curl -s -X POST "$API_URL/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the core principles of CBT?"}')

echo "Chat response: $CHAT_RESPONSE"

# 4. Test safety guardrail
echo "Testing safety guardrail..."
SAFETY_RESPONSE=$(curl -s -X POST "$API_URL/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to hurt myself"}')

echo "Safety response: $SAFETY_RESPONSE"
```

## Notes

- In development mode, authentication is simplified (no password required)
- Admin users can be created by using emails ending with `@admin.com`
- The API uses JWT tokens with 60-minute expiration (configurable)
- All responses include appropriate safety checks and citations
- PII in messages is automatically redacted before storage
