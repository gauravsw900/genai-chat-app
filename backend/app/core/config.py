from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    redis_url: str = "redis://localhost:6379"

    app_name: str = "GenAI Chat"
    api_prefix: str = "/api"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_retrieval: int = 5
    vector_store_path: str = "./data/vectorstore"

    max_conversation_history: int = 20
    conversation_ttl_seconds: int = 86400

    max_agent_iterations: int = 10
    agent_timeout_seconds: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
