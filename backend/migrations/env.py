import asyncio
from logging.config import fileConfig
from typing import Any, cast
from app.models import Project, ProjectSource, RefreshToken, User  # noqa: F401
from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from app.core.database_config import DatabaseSettings
from app.models.base import Base


# Importing app.models registers every table with Base.metadata for autogenerate.
_ = (Project, ProjectSource, RefreshToken, User)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic needs only database configuration, not JWT or other app secrets.
database_settings = cast(Any, DatabaseSettings)()
config.set_main_option("sqlalchemy.url", database_settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            # PgBouncer transaction/statement pooling cannot safely reuse
            # asyncpg prepared statements across backend connections.
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations using an asynchronous database connection."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
