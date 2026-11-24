"""Fake extractor for tests and CI: returns prepared answers, costs nothing, needs no network."""

from collections.abc import Callable

from belegfluss.extraction import Extraction
from belegfluss.extraction.prepare import Prepared
from belegfluss.extraction.schema import ExtractedInvoice


class FakeExtractor:
    def __init__(self, answer: Callable[[Prepared], ExtractedInvoice]) -> None:
        self._answer = answer
        self.calls: list[Prepared] = []

    def extract(self, prepared: Prepared) -> Extraction:
        self.calls.append(prepared)
        return Extraction(
            self._answer(prepared), "fake", input_tokens=0, output_tokens=0, seconds=0.0
        )
