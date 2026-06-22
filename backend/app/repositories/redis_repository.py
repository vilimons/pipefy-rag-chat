from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from unicodedata import category, normalize

from redis import Redis
from redis.commands.search.field import NumericField, TagField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import ResponseError

from app.models.schemas import DocumentResponse, SourceChunk, parse_datetime
from app.services.embeddings import embedding_to_bytes
from app.services.ingestion import EmbeddedChunk

DOCUMENT_PREFIX = "document:"
CHUNK_PREFIX = "doc:"
MAX_OVERVIEW_CHUNKS = 10


class RedisDocumentRepository:
    def __init__(
        self,
        redis_client: Redis,
        index_name: str = "docs",
        vector_dim: int = 384,
    ) -> None:
        self.redis_client = redis_client
        self.index_name = index_name
        self.vector_dim = vector_dim

    def ensure_vector_index(self) -> None:
        try:
            self.redis_client.ft(self.index_name).info()
            return
        except ResponseError:
            pass

        schema = (
            VectorField(
                "embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.vector_dim,
                    "DISTANCE_METRIC": "COSINE",
                    "INITIAL_CAP": 1000,
                },
            ),
            TagField("file_id"),
            NumericField("chunk_index"),
        )

        definition = IndexDefinition(
            prefix=[CHUNK_PREFIX],
            index_type=IndexType.HASH,
        )

        try:
            self.redis_client.ft(self.index_name).create_index(
                schema,
                definition=definition,
            )
        except ResponseError as error:
            if "Index already exists" not in str(error):
                raise

    def save_document(
        self,
        file_id: str,
        filename: str,
        uploaded_at: datetime,
        chunks: list[EmbeddedChunk],
    ) -> None:
        self.ensure_vector_index()

        self.redis_client.hset(
            self._document_key(file_id),
            mapping={
                "file_id": file_id,
                "name": filename,
                "uploaded_at": uploaded_at.isoformat(),
                "chunks": len(chunks),
            },
        )

        for chunk in chunks:
            self.redis_client.hset(
                self._chunk_key(file_id, chunk.chunk_index),
                mapping={
                    "file_id": file_id,
                    "source": filename,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "uploaded_at": uploaded_at.isoformat(),
                    "embedding": embedding_to_bytes(chunk.embedding),
                },
            )

    def list_documents(self) -> list[DocumentResponse]:
        documents: list[DocumentResponse] = []

        for key in self.redis_client.scan_iter(f"{DOCUMENT_PREFIX}*"):
            payload = self._decode_hash(self.redis_client.hgetall(key))

            if not payload:
                continue

            documents.append(
                DocumentResponse(
                    file_id=payload["file_id"],
                    name=payload["name"],
                    uploaded_at=parse_datetime(payload["uploaded_at"]),
                    chunks=int(payload["chunks"]),
                )
            )

        return sorted(
            documents,
            key=lambda document: document.uploaded_at,
            reverse=True,
        )

    def delete_document(self, file_id: str) -> bool:
        keys_to_delete = [
            self._document_key(file_id),
            *list(self.redis_client.scan_iter(self._chunk_pattern(file_id))),
        ]

        deleted_count = self.redis_client.delete(*keys_to_delete)

        return deleted_count > 0

    def search_relevant_chunks(
        self,
        question: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[SourceChunk]:
        documents = self.list_documents()

        if not documents:
            return []

        mentioned_documents = self._find_mentioned_documents(
            question=question,
            documents=documents,
        )

        if mentioned_documents:
            return self._get_representative_chunks_for_documents(
                documents=mentioned_documents,
                max_chunks=top_k,
            )

        if self._is_collection_overview_question(question):
            overview_limit = min(
                max(top_k * 2, len(documents) * 2),
                MAX_OVERVIEW_CHUNKS,
            )

            return self._get_representative_chunks_for_documents(
                documents=documents,
                max_chunks=overview_limit,
            )

        return self.search_similar_chunks(
            query_embedding=query_embedding,
            top_k=top_k,
        )

    def search_similar_chunks(
        self,
        query_embedding: list[float],
        top_k: int,
    ) -> list[SourceChunk]:
        self.ensure_vector_index()

        candidate_k = max(top_k * 4, 12)

        query = (
            Query(f"*=>[KNN {candidate_k} @embedding $query_vector AS vector_score]")
            .sort_by("vector_score")
            .return_fields(
                "content",
                "source",
                "file_id",
                "chunk_index",
                "vector_score",
            )
            .paging(0, candidate_k)
            .dialect(2)
        )

        results = self.redis_client.ft(self.index_name).search(
            query,
            query_params={
                "query_vector": embedding_to_bytes(query_embedding),
            },
        )

        chunks = [
            self._search_document_to_source_chunk(document) for document in results.docs
        ]

        return chunks[:top_k]

    def _find_mentioned_documents(
        self,
        question: str,
        documents: list[DocumentResponse],
    ) -> list[DocumentResponse]:
        normalized_question = self._normalize_for_match(question)

        stem_counts = Counter(
            self._normalize_for_match(Path(document.name).stem)
            for document in documents
        )

        matched_documents: list[DocumentResponse] = []

        for document in documents:
            normalized_name = self._normalize_for_match(document.name)
            normalized_stem = self._normalize_for_match(Path(document.name).stem)

            if normalized_name and normalized_name in normalized_question:
                matched_documents.append(document)
                continue

            if (
                len(normalized_stem) >= 4
                and stem_counts[normalized_stem] == 1
                and normalized_stem in normalized_question
            ):
                matched_documents.append(document)

        return matched_documents

    def _is_collection_overview_question(self, question: str) -> bool:
        normalized_question = self._normalize_for_match(question)

        overview_terms = [
            "documentos",
            "arquivos",
            "base de conhecimento",
            "conteudo dos documentos",
            "conteudo dos arquivos",
            "sobre o que tratam",
            "sobre o que falam",
            "do que tratam",
            "do que falam",
            "resuma os documentos",
            "resumo dos documentos",
            "resuma os arquivos",
            "visao geral",
            "todos os documentos",
            "todos os arquivos",
            "o que tem nos documentos",
            "o que tem nos arquivos",
            "informacoes sobre o documento",
            "informacoes do documento",
            "fale sobre o documento",
            "me diga sobre o documento",
            "resuma o documento",
            "resumo do documento",
            "do que se trata o documento",
            "do que trata o documento",
            "documento indexado",
            "arquivo indexado",
            "o que tem no documento",
            "o que tem no arquivo",
            "conteudo do documento",
            "conteudo do arquivo",
            "documents",
            "files",
            "knowledge base",
            "what are the documents about",
            "summarize the documents",
            "summarize the files",
            "overview of the documents",
            "all documents",
            "all files",
        ]

        return any(term in normalized_question for term in overview_terms)

    def _get_representative_chunks_for_documents(
        self,
        documents: list[DocumentResponse],
        max_chunks: int,
    ) -> list[SourceChunk]:
        chunks_by_document = [
            self._get_chunks_for_document(document) for document in documents
        ]

        selected_chunks: list[SourceChunk] = []

        while len(selected_chunks) < max_chunks and any(chunks_by_document):
            for chunks in chunks_by_document:
                if not chunks:
                    continue

                selected_chunks.append(chunks.pop(0))

                if len(selected_chunks) == max_chunks:
                    break

        return selected_chunks

    def _get_chunks_for_document(
        self,
        document: DocumentResponse,
    ) -> list[SourceChunk]:
        chunks: list[SourceChunk] = []

        for key in self.redis_client.scan_iter(self._chunk_pattern(document.file_id)):
            payload = self._decode_hash(self.redis_client.hgetall(key))

            if not payload:
                continue

            chunks.append(
                SourceChunk(
                    chunk=payload["content"],
                    source=payload["source"],
                    score=0.0,
                    chunk_index=int(payload["chunk_index"]),
                    file_id=payload["file_id"],
                )
            )

        return sorted(
            chunks,
            key=lambda chunk: chunk.chunk_index or 0,
        )

    def _select_diverse_chunks(
        self,
        chunks: list[SourceChunk],
        top_k: int,
    ) -> list[SourceChunk]:
        if len(chunks) <= top_k:
            return chunks

        selected: list[SourceChunk] = []
        remaining: list[SourceChunk] = []
        selected_documents: set[str] = set()

        for chunk in chunks:
            document_key = chunk.file_id or chunk.source

            if document_key not in selected_documents:
                selected.append(chunk)
                selected_documents.add(document_key)
            else:
                remaining.append(chunk)

            if len(selected) == top_k:
                return selected

        for chunk in remaining:
            if len(selected) == top_k:
                break

            selected.append(chunk)

        return selected

    def _search_document_to_source_chunk(self, document: Any) -> SourceChunk:
        vector_distance = float(self._decode_value(document.vector_score))

        return SourceChunk(
            chunk=self._decode_value(document.content),
            source=self._decode_value(document.source),
            score=vector_distance,
            chunk_index=int(self._decode_value(document.chunk_index)),
            file_id=self._decode_value(document.file_id),
        )

    def _document_key(self, file_id: str) -> str:
        return f"{DOCUMENT_PREFIX}{file_id}"

    def _chunk_key(self, file_id: str, chunk_index: int) -> str:
        return f"{CHUNK_PREFIX}{file_id}:chunk:{chunk_index}"

    def _chunk_pattern(self, file_id: str) -> str:
        return f"{CHUNK_PREFIX}{file_id}:chunk:*"

    def _decode_hash(self, payload: dict[Any, Any]) -> dict[str, str]:
        decoded_payload: dict[str, str] = {}

        for key, value in payload.items():
            decoded_key = self._decode_value(key)

            if decoded_key == "embedding":
                continue

            decoded_payload[decoded_key] = self._decode_value(value)

        return decoded_payload

    def _decode_value(self, value: Any) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8")

        return str(value)

    def _normalize_for_match(self, value: str) -> str:
        normalized = normalize("NFKD", value.lower())

        return "".join(
            character for character in normalized if category(character) != "Mn"
        )
