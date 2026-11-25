"""Turn recorded answers into scores, with the same code the worker uses.

Azure answers go through `to_invoice_model` and the production checks (`check_invoice`,
`check_ai_invoice`), so a bug in parsing, mapping or verification lowers the score.
"""

import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

from belegfluss.checks import Context, check_invoice
from belegfluss.extraction.schema import ExtractedInvoice, to_invoice_model
from belegfluss.extraction.verify import check_ai_invoice
from belegfluss.reading import InvoiceModel, Source
from belegfluss.reading.model import Line, Party, Totals, VatBreakdown

from belegfluss_eval.manifest import Document
from belegfluss_eval.metrics import Scored, compare, differences
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


def read_azure(answer: dict[str, Any]) -> InvoiceModel | None:
    """The model as the worker would store it; None if the model said it isn't an invoice."""
    extracted = ExtractedInvoice.model_validate(answer)
    return to_invoice_model(extracted) if extracted.is_invoice else None


def _di_amount(value: Any) -> Decimal | None:
    if isinstance(value, dict) and value.get("amount") is not None:
        return Decimal(str(round(float(value["amount"]), 2)))
    return None


def _di_rate(value: Any) -> Decimal | None:
    match = re.search(r"\d+(?:[.,]\d+)?", str(value or ""))
    return Decimal(match.group(0).replace(",", ".")) if match else None


def read_di(answer: dict[str, Any]) -> InvoiceModel | None:
    """Document Intelligence fields mapped onto our model, as plainly as possible.

    Two rules give the baseline the same chance as our reader:
    - without a printed amount due, the total is due (the rule in `to_invoice_model`);
    - tax entries without a rate are left out (DI repeats each tax amount once without its rate).
    """
    payments = [p for p in answer.get("PaymentDetails") or [] if isinstance(p, dict)]
    iban = next((p["IBAN"] for p in payments if p.get("IBAN")), None)
    taxes = [t for t in answer.get("TaxDetails") or [] if isinstance(t, dict) and t.get("Rate")]
    gross = _di_amount(answer.get("InvoiceTotal"))
    due = _di_amount(answer.get("AmountDue"))
    totals = [answer.get(k) for k in ("InvoiceTotal", "AmountDue", "SubTotal")]
    currency = next(
        (v["currency"] for v in totals if isinstance(v, dict) and v.get("currency")), None
    )
    return InvoiceModel(
        number=answer.get("InvoiceId"),
        issue_date=answer.get("InvoiceDate"),
        due_date=answer.get("DueDate"),
        currency=currency,
        seller=Party(name=answer.get("VendorName"), vat_id=answer.get("VendorTaxId")),
        buyer=Party(name=answer.get("CustomerName")),
        ibans=[iban] if iban else [],
        totals=Totals(
            net=_di_amount(answer.get("SubTotal")),
            vat=_di_amount(answer.get("TotalTax")),
            gross=gross,
            due=gross if due is None else due,
        ),
        vat_breakdown=[
            VatBreakdown(rate=_di_rate(t.get("Rate")), tax_amount=_di_amount(t.get("Amount")))
            for t in taxes
        ],
        lines=[Line() for _ in range(int(answer.get("ItemCount") or 0))],
    )


Reader = Callable[[dict[str, Any]], InvoiceModel | None]


def reader_for(header: RunHeader) -> Reader:
    return read_di if header.extractor == "di" else read_azure


def score(doc: Document, recording: Recording, header: RunHeader, reader: Reader) -> Scored:
    model = reader(recording.answer) if recording.answer is not None else None
    if model is None:
        # Failed or "not an invoice": the worker sends it to review with a message, so it is
        # flagged, and every field that the label has counts as wrong.
        model = InvoiceModel()
        fields = compare(doc.labels, model)
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
        differences=differences(doc.labels, model),
        pages=doc.pages,
    )
