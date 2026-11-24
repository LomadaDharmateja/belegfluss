"""Migrations apply to an empty database, can be rolled back, and match the models."""

import uuid

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from belegfluss.models import Base
from tests.conftest import API_ROOT


def _fresh_database(server_url: str) -> str:
    name = f"migration_{uuid.uuid4().hex[:8]}"
    admin = create_engine(server_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    admin.dispose()
    return make_url(server_url).set(database=name).render_as_string(hide_password=False)


def _config(database_url: str) -> Config:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.attributes["database_url"] = database_url
    return config


def test_upgrade_downgrade_upgrade_on_empty_database(postgres_url: str) -> None:
    url = _fresh_database(postgres_url)
    config = _config(url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    assert {"organizations", "users", "memberships", "documents", "audit_events"} <= tables


def test_models_and_migrations_are_in_sync(migrated_db: str) -> None:
    engine = create_engine(migrated_db)
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert differences == [], f"Model changes without a migration: {differences}"
