# ADR-0012: Persistence with sync SQLAlchemy 2.1 + psycopg 3 + Alembic; tests against real PostgreSQL

- **Status:** Accepted (2026-11-24)
- **Date:** 2026-11-23
- **Milestone:** M1

## Context

The API stores organisations, users, memberships, documents and audit events in PostgreSQL (Azure Database for
PostgreSQL Flexible Server from M4; version 18 is GA there). Load is small (a pilot with a handful of users).
Tests must catch real database behaviour: unique constraints, cascades, migrations.

## Options

1. **Async SQLAlchemy** (asyncpg or psycopg async) with async endpoints: higher concurrency per process, but more
   complex code (async sessions, lazy-loading pitfalls) and no benefit at our load.
2. **Sync SQLAlchemy 2.1 + psycopg 3** with sync endpoints: FastAPI runs them in a thread pool. Simple, well
   documented and easy to debug.
3. **SQLModel:** a thin layer combining Pydantic and SQLAlchemy. It's one more abstraction, and we keep API models
   (Pydantic) and tables (SQLAlchemy) separate on purpose.
4. **Testing against SQLite instead of PostgreSQL:** fast, but types, constraints and SQL behave differently.

## Decision

**Option 2**, plus real PostgreSQL in tests.
- Typed models (`Mapped[...]`), one session per request, explicit commits, Alembic migrations. Model and migration
  must match: the test `test_models_and_migrations_are_in_sync` runs Alembic's `compare_metadata`.
- Tests start **PostgreSQL 18 and Azurite with testcontainers**, the same images as Docker Compose. Every test runs
  against the real schema created by the migrations.
- A migration round-trip (upgrade → downgrade → upgrade) is tested on an empty database.
- Locally and in Compose, the API applies migrations on start. In Azure (M4) they run as a separate deployment
  step, so several replicas never migrate at the same time.

## Consequences

- Tests need Docker (available locally and on GitHub runners). The suite took 29.9 s for 63 tests on the dev
  laptop (one run, 2026-11-24), most of it container start-up.
- If concurrency ever becomes a bottleneck, the thread pool size and replicas are tuned first, before switching to
  async (new ADR).

## Sources

- https://docs.sqlalchemy.org/en/21/, https://alembic.sqlalchemy.org/
- Azure PostgreSQL versions: https://learn.microsoft.com/en-us/azure/postgresql/configure-maintain/concepts-version-policy
- https://testcontainers-python.readthedocs.io/
