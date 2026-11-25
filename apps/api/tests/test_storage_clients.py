"""Storage sign-in: Managed Identity in Azure, Azurite connection string locally (ADR-0021)."""

from typing import Any

from azure.core.credentials import AccessToken

from belegfluss import storage_clients
from belegfluss.settings import Settings


class FakeCredential:
    def get_token(self, *scopes: str, **_kwargs: Any) -> AccessToken:
        raise AssertionError("creating a client must not fetch a token")


def test_in_azure_storage_signs_in_with_the_managed_identity_and_no_key() -> None:
    settings = Settings(storage_account="stbelegflussdev", storage_connection_string="")
    credential = FakeCredential()

    blob = storage_clients.blob_service(settings, credential)
    queue = storage_clients.queue_client(settings, "documents", credential)

    assert blob.url == "https://stbelegflussdev.blob.core.windows.net/"
    assert blob.credential is credential
    assert queue.url == "https://stbelegflussdev.queue.core.windows.net/documents"
    assert queue.credential is credential


def test_locally_storage_uses_the_azurite_connection_string() -> None:
    settings = Settings()  # default: UseDevelopmentStorage=true

    assert storage_clients.blob_service(settings).account_name == "devstoreaccount1"
    assert storage_clients.queue_client(settings, "documents").queue_name == "documents"
