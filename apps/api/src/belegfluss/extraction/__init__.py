"""AI reading of documents without structured data (ADR-0016).

The extractor is an interface: Azure OpenAI in development and production, a fake in tests and CI
(no paid calls). Its output is data only and is always checked by code (`verify.py`).
"""

from dataclasses import dataclass
from typing import Protocol

from belegfluss.extraction.prepare import Prepared
from belegfluss.extraction.schema import ExtractedInvoice


@dataclass(frozen=True)
class Extraction:
    invoice: ExtractedInvoice
    model: str
    input_tokens: int
    output_tokens: int
    seconds: float


class ExtractorUnavailableError(Exception):
    """Transient (network, rate limit, service error): the worker retries later."""


class ExtractionFailedError(Exception):
    """Permanent for this document (e.g. refused or incomplete answer). `code` is a finding code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class Extractor(Protocol):
    def extract(self, prepared: Prepared) -> Extraction: ...
