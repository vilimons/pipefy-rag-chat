from functools import lru_cache
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from redis import Redis

from app.core.config import Settings
from app.models.schemas import ChatResponse, SourceChunk
from app.rag.pipeline import build_fallback_answer, build_prompt
from app.repositories.redis_repository import RedisDocumentRepository
from app.services.chat_history import ChatHistoryService, ChatMessage
from app.services.embeddings import EmbeddingService
from app.services.ollama import OllamaClient
from app.services.tracing import LangSmithTracer


class RagGraphState(TypedDict, total=False):
    question: str
    session_id: str
    top_k: int
    settings: Settings
    redis_client: Redis
    embedding_service: EmbeddingService
    ollama_client: OllamaClient
    history_service: ChatHistoryService
    tracer: LangSmithTracer
    metadata: dict[str, Any]
    sources: list[SourceChunk]
    history: list[ChatMessage]
    prompt: str
    answer: str
    response: ChatResponse


def retrieve_sources(
    question: str,
    top_k: int,
    settings: Settings,
    redis_client: Redis,
    embedding_service: EmbeddingService,
) -> list[SourceChunk]:
    query_embedding = embedding_service.embed_text(question)

    repository = RedisDocumentRepository(
        redis_client=redis_client,
        index_name=settings.redis_index_name,
        vector_dim=settings.redis_vector_dim,
    )

    return repository.search_relevant_chunks(
        question=question,
        query_embedding=query_embedding,
        top_k=top_k,
    )


def retriever_node(state: RagGraphState) -> RagGraphState:
    tracer = state["tracer"]

    sources = tracer.trace(
        name="redis_vector_retrieval",
        run_type="retriever",
        inputs={
            "question": state["question"],
            "top_k": state["top_k"],
        },
        metadata=state["metadata"],
        function=lambda: retrieve_sources(
            question=state["question"],
            top_k=state["top_k"],
            settings=state["settings"],
            redis_client=state["redis_client"],
            embedding_service=state["embedding_service"],
        ),
    )

    return {"sources": sources}


def history_node(state: RagGraphState) -> RagGraphState:
    history = state["history_service"].get_messages(state["session_id"])

    return {"history": history}


def context_builder_node(state: RagGraphState) -> RagGraphState:
    sources = state.get("sources", [])

    if not sources:
        return {
            "answer": build_fallback_answer(),
            "prompt": "",
        }

    tracer = state["tracer"]
    history = state.get("history", [])

    prompt = tracer.trace(
        name="build_rag_prompt",
        run_type="chain",
        inputs={
            "question": state["question"],
            "source_count": len(sources),
            "history_count": len(history),
        },
        metadata=state["metadata"],
        function=lambda: build_prompt(
            question=state["question"],
            sources=sources,
            history=history,
        ),
    )

    return {"prompt": prompt}


def llm_node(state: RagGraphState) -> RagGraphState:
    existing_answer = state.get("answer")

    if existing_answer:
        return {}

    tracer = state["tracer"]
    sources = state.get("sources", [])

    answer = tracer.trace(
        name="ollama_generate",
        run_type="llm",
        inputs={
            "prompt": state["prompt"],
            "model": state["settings"].ollama_model,
        },
        metadata={
            **state["metadata"],
            "source_count": len(sources),
        },
        function=lambda: state["ollama_client"].generate(state["prompt"]),
    )

    return {"answer": answer}


def response_formatter_node(state: RagGraphState) -> RagGraphState:
    answer = state["answer"]

    state["history_service"].append_exchange(
        session_id=state["session_id"],
        question=state["question"],
        answer=answer,
    )

    response = ChatResponse(
        answer=answer,
        sources=state.get("sources", []),
        session_id=state["session_id"],
    )

    return {"response": response}


@lru_cache
def get_compiled_rag_graph():
    graph = StateGraph(RagGraphState)

    graph.add_node("retriever_node", retriever_node)
    graph.add_node("history_node", history_node)
    graph.add_node("context_builder_node", context_builder_node)
    graph.add_node("llm_node", llm_node)
    graph.add_node("response_formatter_node", response_formatter_node)

    graph.add_edge(START, "retriever_node")
    graph.add_edge("retriever_node", "history_node")
    graph.add_edge("history_node", "context_builder_node")
    graph.add_edge("context_builder_node", "llm_node")
    graph.add_edge("llm_node", "response_formatter_node")
    graph.add_edge("response_formatter_node", END)

    return graph.compile()


def run_rag_graph(
    question: str,
    session_id: str,
    top_k: int,
    settings: Settings,
    redis_client: Redis,
    embedding_service: EmbeddingService,
    ollama_client: OllamaClient,
    history_service: ChatHistoryService,
    tracer: LangSmithTracer,
) -> ChatResponse:
    metadata = {
        "session_id": session_id,
        "top_k": top_k,
        "llm_provider": "ollama",
        "llm_model": settings.ollama_model,
        "embedding_model": settings.embedding_model_name,
        "environment": settings.app_env,
        "orchestrator": "langgraph",
    }

    graph = get_compiled_rag_graph()

    result = graph.invoke(
        {
            "question": question,
            "session_id": session_id,
            "top_k": top_k,
            "settings": settings,
            "redis_client": redis_client,
            "embedding_service": embedding_service,
            "ollama_client": ollama_client,
            "history_service": history_service,
            "tracer": tracer,
            "metadata": metadata,
        }
    )

    return result["response"]
