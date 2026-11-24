"""The committed OpenAPI file (used to generate the web client) must match the API (ADR-0011)."""

from belegfluss.openapi_export import schema_json
from tests.conftest import REPO_ROOT

CONTRACT = REPO_ROOT / "apps" / "web" / "src" / "api" / "openapi.json"


def test_committed_openapi_matches_the_api() -> None:
    assert CONTRACT.exists(), f"missing {CONTRACT}"
    assert CONTRACT.read_text(encoding="utf-8") == schema_json(), (
        "API changed: run `uv run python -m belegfluss.openapi_export ../web/src/api/openapi.json` "
        "and `pnpm --filter @belegfluss/web gen:api`"
    )
