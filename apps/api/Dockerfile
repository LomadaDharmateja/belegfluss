# syntax=docker/dockerfile:1
# Belegfluss API: FastAPI on Python 3.14. Build context: apps/api

FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# Dependencies first (cached layer), then the project itself.
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.14-slim AS runtime
RUN useradd --system --uid 10001 --no-create-home app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY alembic.ini ./
COPY migrations ./migrations
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/health').status != 200)"]
# Local/dev: apply migrations on start. In Azure (M4) migrations run as a separate job.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn belegfluss.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers"]
