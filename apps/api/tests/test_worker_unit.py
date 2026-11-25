"""Worker settings that must fit together (no containers needed)."""

from collections.abc import Iterator
from typing import Any, cast

from belegfluss import worker
from belegfluss.extraction import azure_openai
from belegfluss.pipeline import Services
from belegfluss.queue import DocumentQueue, Job
from belegfluss.validation import DEFAULT_TIMEOUT_SECONDS


def test_a_message_stays_hidden_longer_than_its_processing_can_take() -> None:
    # Regression: the worker took 4 messages at once, each hidden for 300 s, and processed them one
    # after the other. One document can take 390 s (AI: 3 attempts of 120 s; validator: 30 s), so a
    # message could reappear while it was still waiting, and a second worker replica (KEDA) would
    # read the same document again.
    attempts = azure_openai.MAX_RETRIES + 1
    per_document = azure_openai.REQUEST_TIMEOUT_SECONDS * attempts + DEFAULT_TIMEOUT_SECONDS
    assert worker.JOBS_PER_RECEIVE * per_document < worker.VISIBILITY_TIMEOUT_SECONDS


class RecordingQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def receive(self, max_jobs: int, visibility_timeout: int) -> Iterator[Job]:
        self.calls.append((max_jobs, visibility_timeout))
        return iter(())


def test_the_worker_takes_one_message_at_a_time() -> None:
    queue = RecordingQueue()
    services = cast(Services, None)  # not used when the queue is empty
    w = worker.Worker(services, cast(DocumentQueue, cast(Any, queue)))
    assert w.run_once() == 0
    assert queue.calls == [(1, worker.VISIBILITY_TIMEOUT_SECONDS)]
