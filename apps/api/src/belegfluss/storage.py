"""Blob storage for original files. Originals are never modified (ARCHITECTURE §4)."""

import contextlib
import uuid
from typing import BinaryIO

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings


class BlobStore:
    def __init__(self, connection_string: str, container: str) -> None:
        service = BlobServiceClient.from_connection_string(connection_string)
        self._container = service.get_container_client(container)

    @staticmethod
    def original_name(org_id: uuid.UUID, sha256: str) -> str:
        return f"orgs/{org_id}/originals/{sha256}"

    def put_original(self, org_id: uuid.UUID, sha256: str, data: BinaryIO, media_type: str) -> str:
        """Store the bytes under their hash. Storing the same content twice is a no-op."""
        name = self.original_name(org_id, sha256)
        try:
            self._upload(name, data, media_type)
        except ResourceNotFoundError:
            # First upload in a fresh environment: the container doesn't exist yet.
            self._create_container()
            data.seek(0)
            self._upload(name, data, media_type)
        return name

    def read(self, name: str) -> bytes:
        return self._container.download_blob(name).readall()

    def _upload(self, name: str, data: BinaryIO, media_type: str) -> None:
        # Same name means same SHA-256 means same bytes, so an existing blob is fine.
        with contextlib.suppress(ResourceExistsError):
            self._container.upload_blob(
                name,
                data,
                overwrite=False,
                content_settings=ContentSettings(content_type=media_type),
            )

    def _create_container(self) -> None:
        with contextlib.suppress(ResourceExistsError):
            self._container.create_container()
