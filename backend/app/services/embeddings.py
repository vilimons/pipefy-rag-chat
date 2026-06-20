from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_text(self, text: str) -> list[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        return [float(value) for value in embedding]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return [[float(value) for value in embedding] for embedding in embeddings]


def embedding_to_bytes(embedding: list[float]) -> bytes:
    return np.array(embedding, dtype=np.float32).tobytes()


def embedding_from_bytes(value: bytes) -> list[float]:
    return np.frombuffer(value, dtype=np.float32).tolist()


@lru_cache
def get_embedding_service(model_name: str) -> EmbeddingService:
    return EmbeddingService(model_name=model_name)
