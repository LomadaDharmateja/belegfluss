"""Configuration from environment variables (prefix BELEGFLUSS_). Documented in /.env.example."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BELEGFLUSS_", extra="ignore")

    database_url: str = "postgresql+psycopg://belegfluss:belegfluss-dev@localhost:5432/belegfluss"

    # Local development uses Azurite. In Azure (M4) this becomes an account URL + Managed Identity.
    blob_connection_string: str = "UseDevelopmentStorage=true"
    blob_container: str = "documents"

    # Values from the tenant's OpenID discovery document
    # (https://<subdomain>.ciamlogin.com/<tenant-id>/v2.0/.well-known/openid-configuration).
    auth_issuer: str = ""
    auth_jwks_url: str = ""
    auth_audience: str = ""  # the API's application (client) ID
    auth_required_scope: str = "access_as_user"

    cors_origins: list[str] = ["http://localhost:3000"]
    max_upload_bytes: int = 20 * 1024 * 1024
