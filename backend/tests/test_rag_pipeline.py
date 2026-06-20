from app.models.schemas import SourceChunk
from app.rag.pipeline import build_answer_from_sources


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
