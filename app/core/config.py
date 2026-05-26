from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_NAME: str = "fastapi-app"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://postgres:1234@localhost:5432/appdb"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False  # set True to dump SQL → detect N+1

    REDIS_URL: str = "redis://localhost:6379"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    SENTRY_DSN: str = ""
    ENABLE_METRICS: str = "true"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
