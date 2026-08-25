"""Alembic environment.

The database URL comes from app.config (i.e. from .env), not from alembic.ini, so
there is exactly one place a connection string is written down and no chance of
the two drifting apart.

Everyday use:

    alembic upgrade head                              # after every pull
    alembic revision --autogenerate -m "add users"    # after changing tables.py
    alembic downgrade -1                              # undo the last one
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.tables import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate compares this against the live database to work out the diff.
target_metadata = Base.metadata

# Only fall back to .env when nothing set a URL programmatically -- the test
# suite migrates TEST_DATABASE_URL through this same env.py, and must not be
# quietly redirected onto the development database.
if not config.get_main_option("sqlalchemy.url", None):
    # Escape any % in a password so ConfigParser interpolation does not eat it.
    config.set_main_option(
        "sqlalchemy.url", get_settings().DATABASE_URL.replace("%", "%%")
    )


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it: `alembic upgrade head --sql`."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Without this, changing NUMERIC(18,2) to NUMERIC(20,4) autogenerates
            # an empty migration and the mismatch ships silently.
            compare_type=True,
            # Same for a column gaining or losing a server default.
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
