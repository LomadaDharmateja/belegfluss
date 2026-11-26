"""Azure Storage clients for blobs and queues (ADR-0021).

- In Azure: `BELEGFLUSS_STORAGE_ACCOUNT` is set, and the clients sign in with the Managed Identity.
  The storage account has shared-key access switched off, so there is no key to leak.
- Locally and in CI: the Azurite connection string (`BELEGFLUSS_STORAGE_CONNECTION_STRING`).
"""

from azure.core.credentials import TokenCredential
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient

from belegfluss.identity import azure_credential
from belegfluss.settings import Settings


def blob_service(
    settings: Settings, credential: TokenCredential | None = None
) -> BlobServiceClient:
    if settings.storage_account:
        url = f"https://{settings.storage_account}.blob.core.windows.net"
        return BlobServiceClient(url, credential=credential or azure_credential())
    return BlobServiceClient.from_connection_string(settings.storage_connection_string)


def queue_client(
    settings: Settings, name: str, credential: TokenCredential | None = None
) -> QueueClient:
    if settings.storage_account:
        url = f"https://{settings.storage_account}.queue.core.windows.net"
        return QueueClient(url, name, credential=credential or azure_credential())
    return QueueClient.from_connection_string(settings.storage_connection_string, name)
