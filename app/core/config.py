from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Critique"
    log_level: str = "INFO"
    environment: str = "development"  # "development" | "production"

    # Database
    # Railway and most managed Postgres providers deliver postgresql:// URLs.
    # SQLAlchemy async requires postgresql+asyncpg://.
    # The validator below converts automatically so you can paste the URL as-is.
    database_url: str = "postgresql+asyncpg://critique:critique@localhost:5432/critique"

    @field_validator("database_url", mode="before")
    @classmethod
    def _coerce_db_url_scheme(cls, v: object) -> object:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # LLM
    llm_provider: str = "anthropic"  # "anthropic" | "openai"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Agent tuning
    max_revisions: int = 3
    critic_approval_threshold: float = 0.75
    max_research_results: int = 5
    request_timeout_seconds: int = 30

    # Celery + Redis
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Auth
    api_key: str = ""

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key)

    # CORS — comma-separated list of allowed origins
    # Example: CORS_ORIGINS=http://localhost:3000,https://critique.example.com
    cors_origins_str: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_str.split(",") if o.strip()]

    # Human-in-the-loop default
    human_in_loop: bool = False

    # Optional Tavily key (falls back to DuckDuckGo if empty)
    tavily_api_key: str = ""

    @property
    def use_tavily(self) -> bool:
        return bool(self.tavily_api_key)


settings = Settings()
