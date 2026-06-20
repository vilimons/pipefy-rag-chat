from app.models.schemas import SourceChunk
from app.rag.pipeline import (
    build_answer_from_sources,
    build_fallback_answer,
    build_prompt,
    format_history,
)
from app.services.chat_history import ChatMessage


def test_build_fallback_answer_returns_no_context_message() -> None:
    answer = build_fallback_answer()

    assert "could not find relevant information" in answer


def test_format_history_returns_default_when_empty() -> None:
    assert format_history([]) == "No previous conversation."


def test_format_history_returns_messages() -> None:
    history = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi"),
    ]

    formatted = format_history(history)

    assert "user: Hello" in formatted
    assert "assistant: Hi" in formatted


def test_build_answer_from_sources_returns_fallback_when_no_sources() -> None:
    answer = build_answer_from_sources(
        question="What is Pipefy?",
        sources=[],
    )

    assert "could not find relevant information" in answer


def test_build_answer_from_sources_uses_retrieved_context() -> None:
    sources = [
        SourceChunk(
            chunk="Pipefy is a platform for workflow management.",
            source="pipefy.txt",
            score=0.1,
            chunk_index=0,
            file_id="file-1",
        )
    ]

    answer = build_answer_from_sources(
        question="What is Pipefy?",
        sources=sources,
    )

    assert "What is Pipefy?" in answer
    assert "Pipefy is a platform for workflow management." in answer


def test_build_prompt_includes_question_context_and_history() -> None:
    sources = [
        SourceChunk(
            chunk="Pipefy is used for workflow management.",
            source="pipefy.txt",
            score=0.1,
            chunk_index=0,
            file_id="file-1",
        )
    ]
    history = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi"),
    ]

    prompt = build_prompt(
        question="What is Pipefy used for?",
        sources=sources,
        history=history,
    )

    assert "What is Pipefy used for?" in prompt
    assert "Pipefy is used for workflow management." in prompt
    assert "user: Hello" in prompt
    assert "assistant: Hi" in prompt
    assert "Do not use external knowledge." in prompt
