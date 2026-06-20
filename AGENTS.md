# AGENTS.md — AI Coding Governance

This project is a technical case for a full-stack RAG chat application.

## Prime Directive

Build a working, maintainable, testable end-to-end application:

Upload PDF/TXT → chunk text → embed chunks → index vectors in Redis → retrieve relevant chunks → answer with local LLM → show answer and sources in React.

## Non-negotiable Rules

- Do not commit secrets.
- Do not hardcode API keys, model names, Redis URLs or ports.
- Use environment variables through backend/app/core/config.py.
- Keep routers thin; business logic belongs in services, repositories or rag modules.
- Use type hints in Python.
- Use Pydantic schemas for request/response models.
- Use pytest for backend tests.
- Mock external dependencies in tests.
- Do not copy large code blocks from reference repositories.
- Prefer simple, working code over over-engineered abstractions.
- Every endpoint must return predictable JSON.
- Every RAG answer must include sources.

## Agent Roles

### Backend Agent
Responsible for FastAPI routes, schemas, dependency wiring and error handling.

### RAG Agent
Responsible for chunking, embeddings, Redis vector search, LangGraph flow and prompt construction.

### Frontend Agent
Responsible for React UI, upload flow, document list, chat messages, loading states and source display.

### Test Agent
Responsible for pytest coverage, mocks, endpoint tests and regression checks.

### DevOps Agent
Responsible for Dockerfiles, docker-compose, env files, health checks and Makefile commands.

### Documentation Agent
Responsible for README, architecture notes, trade-offs and run instructions.

## Validation Before Marking Work Complete

Run at least:

```bash
make test
docker compose up --build
