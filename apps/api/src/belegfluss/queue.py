"""Processing jobs on Azure Storage Queue (Azurite locally), ADR-0004.

A message carries only the document ID. The database status is the source of truth; the queue only
says "please look at this document". Messages that keep failing go to `<queue>-poison`.
"""

import contextlib
import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.queue import QueueClient

from belegfluss import storage_clients
from belegfluss.settings import Settings


@dataclass(frozen=True)
class Job:
    message_id: str
    pop_receipt: str
    document_id: uuid.UUID | None  # None if the message is unreadable
    deliveries: int  # how often the message has been received, including this time


class DocumentQueue:
    def __init__(self, queue: QueueClient, poison: QueueClient) -> None:
        self._queue = queue
        self._poison = poison

    @classmethod
    def from_settings(cls, settings: Settings) -> DocumentQueue:
        name = settings.queue_name
        return cls(
            storage_clients.queue_client(settings, name),
            storage_clients.queue_client(settings, f"{name}-poison"),
        )

    def ensure_exists(self) -> None:
        for client in (self._queue, self._poison):
            with contextlib.suppress(ResourceExistsError):
                client.create_queue()

    def send(self, document_id: uuid.UUID) -> None:
        content = json.dumps({"document_id": str(document_id)})
        try:
            self._queue.send_message(content)
        except ResourceNotFoundError:
            self.ensure_exists()
            self._queue.send_message(content)

    def receive(self, max_jobs: int, visibility_timeout: int) -> Iterator[Job]:
        """Received messages stay invisible for `visibility_timeout` seconds; delete when done."""
        for message in self._queue.receive_messages(
            max_messages=max_jobs, visibility_timeout=visibility_timeout
        ):
            yield Job(
                message_id=message.id,
                pop_receipt=message.pop_receipt or "",
                document_id=_document_id(message.content),
                deliveries=message.dequeue_count or 1,
            )

    def retry_later(self, job: Job, delay_seconds: int) -> None:
        """Make the message visible again after `delay_seconds` (instead of the long timeout)."""
        self._queue.update_message(
            job.message_id, job.pop_receipt, visibility_timeout=delay_seconds
        )

    def delete(self, job: Job) -> None:
        self._queue.delete_message(job.message_id, job.pop_receipt)

    def poison(self, job: Job) -> None:
        """Move a job that keeps failing to the poison queue (kept for inspection)."""
        self._poison.send_message(json.dumps({"document_id": str(job.document_id)}))
        self.delete(job)

    def peek_poison(self) -> list[str]:
        return [m.content for m in self._poison.peek_messages(max_messages=32)]


def _document_id(content: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(json.loads(str(content))["document_id"])
    except ValueError, KeyError, TypeError:
        return None
