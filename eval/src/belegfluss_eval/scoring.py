"""Turn recorded answers into scores, with the same code the worker uses.

Azure answers go through `to_invoice_model` and the production checks (`check_invoice`,
`check_ai_invoice`), so a bug in parsing, mapping or verification lowers the score.
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from belegfluss.checks import Context, check_invoice
from belegfluss.extraction.schema import ExtractedInvoice, to_invoice_model
from belegfluss.extraction.verify import check_ai_invoice
from belegfluss.reading import InvoiceModel, Source

from belegfluss_eval.manifest import Document
from belegfluss_eval.metrics import Scored, compare
from belegfluss_eval.recording import Recording, RunHeader

# USD per token, Azure Retail Prices API 2026-11-24, Data Zone (ADR-0016, COSTS.md).
PRICES = {"gpt-5.4-mini": (Decimal("0.825") / 1_000_000, Decimal("4.95") / 1_000_000)}
DI_PRICE_PER_PAGE = Decimal("0.01")  # S0 prebuilt; F0 is free, but cost is reported as if paid

# Findings that check the *reading* (ADR-0006: formats, sums, presence, VAT-rate plausibility).
# Mandatory-detail findings (missing address, delivery date, ...) are about the invoice itself, so
# they don't count as catching or missing a reading error.
VERIFICATION_CODES = frozenset(
    {
        "BF-AI-IMPLAUSIBLE-DATE",
        "BF-AI-INVALID-IBAN",
        "BF-AI-INVALID-VAT-ID",
        "BF-AI-NOT-IN-DOCUMENT",
        "BF-TOTAL-GROSS",
        "BF-TOTAL-LINES",
        "BF-VAT-AMOUNT",
        "BF-VAT-RATE-UNUSUAL",
    }
)


def cost_usd(header: RunHeader, recording: Recording, pages: int) -> float:
    if header.extractor == "di":
        return float(DI_PRICE_PER_PAGE * min(pages, 2))
    price_in, price_out = PRICES.get(header.deployment or "", (Decimal(0), Decimal(0)))
    return float(recording.input_tokens * price_in + recording.output_tokens * price_out)


def _flagged(model: InvoiceModel, text: str, today: date) -> bool:
    findings = check_invoice(model, Context(source=Source.AI, validator_ran=False))
    findings += check_ai_invoice(model, text, today)
    return any(f.code in VERIFICATION_CODES and f.severity != "info" for f in findings)


def read_azure(answer: dict[str, object]) -> InvoiceModel | None:
    """The model as the worker would store it; None if the model said it isn't an invoice."""
    extracted = ExtractedInvoice.model_validate(answer)
    return to_invoice_model(extracted) if extracted.is_invoice else None


Reader = Callable[[dict[str, object]], InvoiceModel | None]


def score(doc: Document, recording: Recording, header: RunHeader, reader: Reader) -> Scored:
    model = reader(recording.answer) if recording.answer is not None else None
    if model is None:
        # Failed or "not an invoice": the worker sends it to review with a message, so it is
        # flagged, and every field that the label has counts as wrong.
        fields = compare(doc.labels, InvoiceModel())
        flagged = True
    else:
        fields = compare(doc.labels, model)
        flagged = _flagged(model, recording.text, header.today)
    return Scored(
        doc_id=doc.id,
        group=f"{doc.source}/{doc.variant}",
        fields=fields,
        flagged=flagged,
        cost_usd=cost_usd(header, recording, doc.pages),
        seconds=recording.seconds,
    )
