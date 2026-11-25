"""One sweep, then exit: python -m belegfluss.sweep (ADR-0004, ADR-0021).

In Azure the worker scales to zero when the queue is empty, so the sweep built into its loop doesn't
run. A scheduled Container Apps job runs this instead. It re-enqueues documents that have waited too
long; the worker (woken up by the queue) then processes them.
"""

import logging
from datetime import UTC, datetime

from belegfluss.settings import Settings
from belegfluss.worker import build

logger = logging.getLogger("belegfluss.sweep")


def run(settings: Settings) -> int:
    return build(settings).sweep(datetime.now(UTC))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("azure").setLevel(logging.WARNING)
    logger.info("sweep done: %d document(s) re-enqueued", run(Settings()))


if __name__ == "__main__":
    main()
