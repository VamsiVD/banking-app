"""Settings, read from the environment.

`DATABASE_URL` has no default on purpose. A fallback like
"postgresql://localhost/banking" looks helpful right up to the moment someone runs
the test suite against their development database and wonders where their data
went. Missing configuration should stop the app, not guess.

Copy `.env.example` to `.env` to get started; `.env` is gitignored.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Unknown keys in .env are the teammate's business, not ours to reject.
        extra="ignore",
    )

    # postgresql+psycopg://user:password@host:port/database
    DATABASE_URL: str

    # Points at a separate database. The test fixtures TRUNCATE between cases, so
    # this must never resolve to the same database as DATABASE_URL.
    TEST_DATABASE_URL: str | None = None

    # Echo every statement SQLAlchemy emits. Useful when a query surprises you.
    SQL_ECHO: bool = False

    # Access tokens. No default for the key: a fallback in source is a secret
    # everyone with the repo already has.
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is read once per process, not once per import."""
    return Settings()