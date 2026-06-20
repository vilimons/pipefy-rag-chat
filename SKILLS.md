# SKILLS.md — Project Implementation Skills

## FastAPI Skill

Use APIRouter modules under backend/app/api/routes.
Each route must delegate to services.
Use Pydantic request/response models.
Return clear HTTP errors with proper status codes.

## Redis Vector Search Skill

Use Redis Stack with RediSearch.
Store chunks as Redis HASH keys using this pattern:

doc:{file_id}:chunk:{chunk_index}

Each hash should include:
- file_id
- source
- chunk_index
- content
- uploaded_at
- embedding as FLOAT32 bytes

Create a vector index with:
- HNSW
- FLOAT32
- DIM from REDIS_VECTOR_DIM
- COSINE distance

## RAG Skill

RAG flow:
1. Embed question using the same embedding model used for documents.
2. Retrieve top_k chunks from Redis.
3. Build context from chunks and recent session history.
4. Call Ollama local LLM.
5. Return answer plus sources.

Prefer LangGraph for orchestration:
- retriever_node
- context_builder_node
- llm_node
- response_formatter_node

## Testing Skill

Use pytest.
Mock embeddings and LLM calls.
Use FastAPI TestClient or httpx.
Test:
- health endpoint
- text chunking
- upload flow
- document listing
- document deletion
- chat response with mocked retriever and mocked LLM

## Frontend Skill

Use React + Vite.
Keep UI simple:
- File upload
- Document list
- Chat window
- Sources display
- Loading states
- Error messages

Avoid complex state management unless necessary.
