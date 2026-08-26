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

    # Signs and verifies access tokens. No default, for the same reason
    # DATABASE_URL has none: a fallback secret committed to the repo is a
    # secret everyone already has, which is the same as having none. Missing
    # it stops the app at startup rather than shipping forgeable tokens.
    JWT_SECRET_KEY: str

    # HMAC-SHA256: one shared secret both signs and verifies. Not a secret
    # itself, so a default is fine. Named once here so create and decode
    # cannot drift apart.
    JWT_ALGORITHM: str = "HS256"

    # There is no server-side logout in this design, so a stolen token stays
    # good until it expires. That is the whole argument for 30 minutes rather
    # than 30 days; revoking early would need a denylist we are not building.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is read once per process, not once per import."""
    return Settings()
