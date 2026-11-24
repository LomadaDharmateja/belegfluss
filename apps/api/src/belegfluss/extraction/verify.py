"""Checks for AI-read invoices (ADR-0006, ADR-0016): confidence comes from code, not from the model.

- formats: IBAN checksum, VAT ID shape, plausible dates
- presence: the value the model returned must appear in the document's own text layer (PDFs with
  text). A value that isn't there may be misread, or invented by the model.

Everything here is a hint for the person who reviews the document.
"""

import re
from datetime import date, timedelta
from decimal import Decimal

from belegfluss.checks import CheckFinding, amounts_in_text, normalise_text
from belegfluss.reading import InvoiceModel

# DE: "DE" + 9 digits. Other EU countries: two letters + 2-12 letters/digits (shape only).
_VAT_ID = re.compile(r"^(DE\d{9}|(?!DE)[A-Z]{2}[0-9A-Z+*.]{2,12})$")
_EARLIEST = date(2000, 1, 1)


def iban_is_valid(iban: str) -> bool:
    """ISO 13616 check digits (mod 97)."""
    compact = re.sub(r"\s+", "", iban).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", compact):
        return False
    rearranged = compact[4:] + compact[:4]
    digits = "".join(str(int(char, 36)) for char in rearranged)
    return int(digits) % 97 == 1


def check_formats(invoice: InvoiceModel, today: date) -> list[CheckFinding]:
    findings = [
        CheckFinding("BF-AI-INVALID-IBAN", "warning", ("BT-84",), {"value": iban})
        for iban in invoice.ibans
        if not iban_is_valid(iban)
    ]
    vat_id = invoice.seller.vat_id
    if vat_id and not _VAT_ID.fullmatch(re.sub(r"\s+", "", vat_id).upper()):
        findings.append(
            CheckFinding("BF-AI-INVALID-VAT-ID", "warning", ("BT-31",), {"value": vat_id})
        )
    issue = invoice.issue_date
    if issue is not None and not _EARLIEST <= issue <= today + timedelta(days=31):
        findings.append(
            CheckFinding("BF-AI-IMPLAUSIBLE-DATE", "warning", ("BT-2",), {"field": "issue_date"})
        )
    if issue is not None and invoice.due_date is not None and invoice.due_date < issue:
        findings.append(
            CheckFinding("BF-AI-IMPLAUSIBLE-DATE", "warning", ("BT-9",), {"field": "due_date"})
        )
    return findings


def check_presence(invoice: InvoiceModel, text: str) -> list[CheckFinding]:
    """Values that don't appear in the text layer. Nothing to compare for photos and scans."""
    haystack = normalise_text(text)
    if not haystack:
        return []
    candidates: list[tuple[str, str, set[str]]] = []
    missing: list[CheckFinding] = []
    if invoice.number:
        candidates.append(("number", "BT-1", {normalise_text(invoice.number)}))
    if invoice.seller.vat_id:
        candidates.append(("vat_id", "BT-31", {normalise_text(invoice.seller.vat_id)}))
    for iban in invoice.ibans:
        candidates.append(("iban", "BT-84", {normalise_text(iban)}))
    gross = invoice.totals.gross
    if gross is not None and gross.quantize(Decimal("0.01")) not in amounts_in_text(text):
        missing.append(
            CheckFinding("BF-AI-NOT-IN-DOCUMENT", "warning", ("BT-112",), {"field": "gross"})
        )
    return [
        CheckFinding("BF-AI-NOT-IN-DOCUMENT", "warning", (term,), {"field": field})
        for field, term, spellings in candidates
        if not any(spelling in haystack for spelling in spellings)
    ] + missing


def check_ai_invoice(invoice: InvoiceModel, text: str, today: date) -> list[CheckFinding]:
    """All AI-specific checks. The marker finding tells the user that a person must confirm."""
    marker = CheckFinding("BF-AI-READ", "info")
    return [marker, *check_formats(invoice, today), *check_presence(invoice, text)]
