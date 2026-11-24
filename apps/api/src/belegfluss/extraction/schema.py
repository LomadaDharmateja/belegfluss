"""What the model must return (structured outputs, ADR-0016), and how it maps to InvoiceModel.

Strict-mode rules (Microsoft Learn, structured outputs): every field is required but may be null,
no `pattern`/`format`/min/max keywords, at most 100 properties and 5 levels. So amounts and dates
are plain strings here; code parses them and anything unparseable becomes None (then the checks
report it).
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict

from belegfluss.reading.model import Address, InvoiceModel, Line, Party, Totals, VatBreakdown


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractedParty(_Strict):
    name: str | None
    street: str | None
    post_code: str | None
    city: str | None
    country_code: str | None  # ISO 3166-1 alpha-2, e.g. DE
    vat_id: str | None  # USt-IdNr., e.g. DE123456789
    tax_number: str | None  # Steuernummer


class ExtractedLine(_Strict):
    description: str | None
    quantity: str | None
    unit_price: str | None
    net_amount: str | None
    vat_rate: str | None  # percent, e.g. "19"


class ExtractedVat(_Strict):
    rate: str | None  # percent, e.g. "19"
    taxable_amount: str | None
    tax_amount: str | None


class ExtractedInvoice(_Strict):
    is_invoice: bool  # false if the document is not an invoice or receipt
    number: str | None
    issue_date: str | None  # YYYY-MM-DD
    due_date: str | None
    delivery_date: str | None
    currency: str | None  # ISO 4217, e.g. EUR
    seller: ExtractedParty
    buyer: ExtractedParty
    iban: str | None
    lines: list[ExtractedLine]
    vat_breakdown: list[ExtractedVat]
    net_total: str | None
    vat_total: str | None
    gross_total: str | None
    amount_due: str | None


_NOT_DIGITS = re.compile(r"[^\d,.\-]")


def parse_amount(value: str | None) -> Decimal | None:
    """'1234.56', '1.234,56', '1,234.56', '12,50 €' -> Decimal; anything else -> None."""
    if not value:
        return None
    text = _NOT_DIGITS.sub("", value)
    if "," in text and "." in text:
        decimal_mark = "," if text.rfind(",") > text.rfind(".") else "."
        text = text.replace("." if decimal_mark == "," else ",", "")
    text = text.replace(",", ".")
    try:
        return Decimal(text) if text not in ("", "-", ".") else None
    except InvalidOperation:
        return None


def parse_date(value: str | None) -> date | None:
    """'2026-11-18' or '18.11.2026' -> date; anything else -> None."""
    if not value:
        return None
    text = value.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return date.fromisoformat(text)
        match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
        return date(int(match[3]), int(match[2]), int(match[1])) if match else None
    except ValueError:
        return None


def _party(party: ExtractedParty) -> Party:
    return Party(
        name=party.name,
        vat_id=party.vat_id.replace(" ", "").upper() if party.vat_id else None,
        tax_number=party.tax_number,
        address=Address(
            line1=party.street,
            city=party.city,
            post_code=party.post_code,
            country_code=party.country_code,
        ),
    )


def to_invoice_model(extracted: ExtractedInvoice) -> InvoiceModel:
    vat_breakdown = []
    for vat in extracted.vat_breakdown:
        rate = parse_amount(vat.rate)
        vat_breakdown.append(
            VatBreakdown(
                category="S" if rate is not None and rate > 0 else None,
                rate=rate,
                taxable_amount=parse_amount(vat.taxable_amount),
                tax_amount=parse_amount(vat.tax_amount),
            )
        )
    return InvoiceModel(
        number=extracted.number,
        issue_date=parse_date(extracted.issue_date),
        type_code="380",
        currency=extracted.currency.upper() if extracted.currency else None,
        due_date=parse_date(extracted.due_date),
        delivery_date=parse_date(extracted.delivery_date),
        seller=_party(extracted.seller),
        buyer=_party(extracted.buyer),
        ibans=[extracted.iban.replace(" ", "").upper()] if extracted.iban else [],
        totals=Totals(
            net=parse_amount(extracted.net_total),
            vat=parse_amount(extracted.vat_total),
            gross=parse_amount(extracted.gross_total),
            due=parse_amount(extracted.amount_due),
        ),
        vat_breakdown=vat_breakdown,
        lines=[
            Line(
                name=line.description,
                quantity=parse_amount(line.quantity),
                unit_price=parse_amount(line.unit_price),
                net_amount=parse_amount(line.net_amount),
                vat_rate=parse_amount(line.vat_rate),
            )
            for line in extracted.lines
        ],
    )
