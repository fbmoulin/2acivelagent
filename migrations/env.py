"""
Sistema de Automacao Juridica - Alembic Migration Environment

This module configures the Alembic migration environment.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models for autogenerate support
from migrations.models import Base

# Alembic Config object
config = context.config

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model's MetaData for autogenerate support
target_metadata = Base.metadata


def get_url():
    """Get database URL from environment variables.

    Raises:
        RuntimeError: If required database credentials are not configured.
    """
    # Try full URL first
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if url:
        return url

    # Build URL from individual components - password is REQUIRED
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError(
            "Database credentials not configured. "
            "Set DATABASE_URL or POSTGRES_PASSWORD environment variable."
        )

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "n8n")
    user = os.getenv("POSTGRES_USER", "n8n_user")

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
