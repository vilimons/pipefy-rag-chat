from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "pipefy-rag-chat"
    app_env: str = "development"

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_index_name: str = "docs"
    redis_vector_dim: int = 384

    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    max_history_messages: int = 6

    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.1:8b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
