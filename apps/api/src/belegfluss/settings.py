"""Configuration from environment variables (prefix BELEGFLUSS_). Documented in /.env.example."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BELEGFLUSS_", extra="ignore")

    database_url: str = "postgresql+psycopg://belegfluss:belegfluss-dev@localhost:5432/belegfluss"
    # Azure (ADR-0021): the URL has no password; each connection signs in with a Microsoft Entra
    # token of the Managed Identity (the user name is the identity's database role).
    database_entra_auth: bool = False

    # Blob (originals) and Queue (processing jobs) in one storage account. Locally: Azurite and its
    # connection string. In Azure: the account name, and the Managed Identity signs in (no key).
    storage_connection_string: str = "UseDevelopmentStorage=true"
    storage_account: str = ""
    blob_container: str = "documents"
    queue_name: str = "documents"

    # Values from the tenant's OpenID discovery document
    # (https://<subdomain>.ciamlogin.com/<tenant-id>/v2.0/.well-known/openid-configuration).
    auth_issuer: str = ""
    auth_jwks_url: str = ""
    auth_audience: str = ""  # the API's application (client) ID
    auth_required_scope: str = "access_as_user"

    cors_origins: list[str] = ["http://localhost:3000"]
    max_upload_bytes: int = 20 * 1024 * 1024
    max_pdf_pages: int = 50

    # Official KoSIT validator daemon on the internal network (ADR-0005). The configuration version
    # is stored with every result. It must match services/validator/Dockerfile (checked by a test).
    validator_url: str = "http://localhost:8081"
    validator_config: str = "xrechnung-3.0.2-2026-08-31"

    # AI reading of plain PDFs and photos (ADR-0016). Empty endpoint = off (Compose default, CI).
    # Keyless: the worker signs in with Microsoft Entra ID (az login locally, Managed Identity
    # in M4).
    openai_endpoint: str = ""  # https://<resource>.openai.azure.com
    openai_deployment: str = "gpt-5.4-mini"
    ai_max_pages: int = 3
    ai_reasoning_effort: str = "low"
