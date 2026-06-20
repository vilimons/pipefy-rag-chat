import pytest

from app.services.chunking import split_text_into_chunks


def test_split_text_into_chunks_returns_single_chunk_for_short_text() -> None:
    chunks = split_text_into_chunks(
        text="hello world",
        chunk_size=100,
        chunk_overlap=10,
    )

    assert len(chunks) == 1
    assert chunks[0].content == "hello world"
    assert chunks[0].chunk_index == 0


def test_split_text_into_chunks_applies_overlap() -> None:
    chunks = split_text_into_chunks(
        text="abcdefghij",
        chunk_size=4,
        chunk_overlap=1,
    )

    assert [chunk.content for chunk in chunks] == ["abcd", "defg", "ghij"]


def test_split_text_into_chunks_returns_empty_list_for_blank_text() -> None:
    assert split_text_into_chunks("   ", chunk_size=10, chunk_overlap=2) == []


def test_split_text_into_chunks_rejects_invalid_chunk_size() -> None:
    with pytest.raises(ValueError, match="chunk_size"):
        split_text_into_chunks("hello", chunk_size=0, chunk_overlap=0)


def test_split_text_into_chunks_rejects_negative_overlap() -> None:
    with pytest.raises(ValueError, match="overlap"):
        split_text_into_chunks("hello", chunk_size=10, chunk_overlap=-1)


def test_split_text_into_chunks_rejects_overlap_too_large() -> None:
    with pytest.raises(ValueError, match="overlap"):
        split_text_into_chunks("hello", chunk_size=10, chunk_overlap=10)
