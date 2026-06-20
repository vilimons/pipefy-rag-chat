from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    content: str
    chunk_index: int


def split_text_into_chunks(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    normalized_text = text.strip()

    if not normalized_text:
        return []

    chunks: list[TextChunk] = []
    start = 0
    chunk_index = 0
    text_length = len(normalized_text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk_content = normalized_text[start:end].strip()

        if chunk_content:
            chunks.append(TextChunk(content=chunk_content, chunk_index=chunk_index))
            chunk_index += 1

        if end == text_length:
            break

        start = end - chunk_overlap

    return chunks
