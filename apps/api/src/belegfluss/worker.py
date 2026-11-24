"""Background worker (ADR-0004). Run with: python -m belegfluss.worker

- takes jobs from the queue and processes documents (pipeline.py)
- transient errors (validator or storage unavailable): the message becomes visible again and is
  retried
- after MAX_DELIVERIES attempts the document becomes `failed`; the message goes to the poison queue
- a sweeper re-enqueues documents stuck in `received` (enqueue failed) or `processing` (crashed)

Logs contain document IDs and error types only, never file names or invoice content.
"""

import logging
import signal
import time
from datetime import UTC, datetime, timedelta
from types import FrameType

from azure.core.exceptions import AzureError
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import OperationalError

from belegfluss.db import make_session_factory
from belegfluss.models import Document, DocumentStatus
from belegfluss.pipeline import Services, mark_failed, process_document
from belegfluss.queue import DocumentQueue, Job
from belegfluss.settings import Settings
from belegfluss.storage import BlobStore
from belegfluss.validation import ValidatorClient, ValidatorUnavailableError

logger = logging.getLogger("belegfluss.worker")

MAX_DELIVERIES = 5
VISIBILITY_TIMEOUT_SECONDS = 300
STUCK_IN_RECEIVED = timedelta(minutes=2)
STUCK_IN_PROCESSING = timedelta(minutes=15)
SWEEP_EVERY_SECONDS = 60
IDLE_SLEEP_SECONDS = 2.0
TRANSIENT = (ValidatorUnavailableError, AzureError, OperationalError)


class Worker:
    def __init__(
        self,
        services: Services,
        queue: DocumentQueue,
        *,
        visibility_timeout: int = VISIBILITY_TIMEOUT_SECONDS,
        max_deliveries: int = MAX_DELIVERIES,
    ) -> None:
        self.services = services
        self.queue = queue
        self.visibility_timeout = visibility_timeout
        self.max_deliveries = max_deliveries

    def run_once(self) -> int:
        """Handle the jobs that are waiting now. Returns how many were received."""
        jobs = list(self.queue.receive(max_jobs=4, visibility_timeout=self.visibility_timeout))
        for job in jobs:
            self._handle(job)
        return len(jobs)

    def _handle(self, job: Job) -> None:
        if job.document_id is None:
            logger.warning("unreadable queue message moved to poison queue")
            self.queue.poison(job)
            return
        if job.deliveries > self.max_deliveries:
            logger.warning(
                "document %s: giving up after %d attempts", job.document_id, job.deliveries - 1
            )
            mark_failed(job.document_id, self.services, "processing.gave_up")
            self.queue.poison(job)
            return
        try:
            process_document(job.document_id, self.services)
        except TRANSIENT as exc:
            logger.warning("document %s: will retry (%s)", job.document_id, type(exc).__name__)
            return  # not deleted: the message becomes visible again after the visibility timeout
        except Exception as exc:
            # Unexpected (a bug). Type only: exception text could contain document content.
            logger.error("document %s: unexpected %s", job.document_id, type(exc).__name__)
            return
        self.queue.delete(job)

    def sweep(self, now: datetime) -> int:
        """Re-enqueue documents that have waited too long. Returns how many."""
        with self.services.session_factory.begin() as session:
            stuck = session.scalars(
                select(Document)
                .where(
                    or_(
                        and_(
                            Document.status == DocumentStatus.RECEIVED,
                            Document.status_changed_at < now - STUCK_IN_RECEIVED,
                        ),
                        and_(
                            Document.status == DocumentStatus.PROCESSING,
                            Document.status_changed_at < now - STUCK_IN_PROCESSING,
                        ),
                    )
                )
                .with_for_update(skip_locked=True)
                .limit(100)
            ).all()
            for document in stuck:
                document.status_changed_at = now  # so the next sweep doesn't send it again at once
            ids = [document.id for document in stuck]
        for document_id in ids:
            self.queue.send(document_id)
        if ids:
            logger.info("sweeper re-enqueued %d document(s)", len(ids))
        return len(ids)


def build(settings: Settings) -> Worker:
    _engine, session_factory = make_session_factory(settings.database_url)
    services = Services(
        session_factory=session_factory,
        blob_store=BlobStore(settings.storage_connection_string, settings.blob_container),
        validator=ValidatorClient(settings.validator_url),
        validator_config=settings.validator_config,
        max_pdf_pages=settings.max_pdf_pages,
    )
    queue = DocumentQueue(settings.storage_connection_string, settings.queue_name)
    queue.ensure_exists()
    return Worker(services, queue)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # The Azure SDK logs every HTTP request with headers at INFO: noise, and storage paths.
    logging.getLogger("azure").setLevel(logging.WARNING)
    worker = build(Settings())
    running = True

    def stop(_signum: int, _frame: FrameType | None) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    logger.info("worker started")
    last_sweep = 0.0
    while running:
        try:
            if time.monotonic() - last_sweep >= SWEEP_EVERY_SECONDS:
                worker.sweep(datetime.now(UTC))
                last_sweep = time.monotonic()
            if worker.run_once() == 0:
                time.sleep(IDLE_SLEEP_SECONDS)
        except TRANSIENT as exc:
            logger.warning("infrastructure unavailable (%s), waiting", type(exc).__name__)
            time.sleep(IDLE_SLEEP_SECONDS * 5)
    logger.info("worker stopped")


if __name__ == "__main__":
    main()
