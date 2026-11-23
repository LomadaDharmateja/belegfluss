# Belegfluss API

FastAPI service: authentication (Entra External ID tokens), organisations, document upload.

```bash
uv sync                      # install (Python 3.14 is downloaded by uv if missing)
uv run pytest                # tests: start real PostgreSQL + Azurite containers (Docker must run)
uv run ruff check . && uv run ruff format --check . && uv run mypy src
uv run python -m belegfluss.openapi_export ../web/src/api/openapi.json   # update the API contract
```

Run the whole stack with Docker Compose from the repository root (see the main README).
Configuration: environment variables with the prefix `BELEGFLUSS_`, documented in `/.env.example`.
