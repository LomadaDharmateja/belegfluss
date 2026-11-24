"""Business checks on a read invoice: plain code, no LLM, no I/O. Codes start with BF-.

Findings are hints for the user ("please check"), not a legal verdict (research F16). Mandatory
details follow the KoSIT/FeRD mapping of § 14 Abs. 4 UStG (F29, a non-binding guide) and
§ 33 UStDV for small amounts (F11).
"""

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from belegfluss.reading import InvoiceModel, Source

CENT = Decimal("0.01")
SMALL_AMOUNT_LIMIT = Decimal(250)  # § 33 UStDV: "Gesamtbetrag 250 Euro nicht übersteigt"
GERMAN_STANDARD_RATES = {Decimal(19), Decimal(7)}  # VAT category "S" in Germany
NOT_AN_E_INVOICE_PROFILES = ("minimum", "basicwl")  # ZUGFeRD/Factur-X profiles, F3


@dataclass(frozen=True)
class CheckFinding:
    code: str
    severity: str  # error | warning | info
    business_terms: tuple[str, ...] = ()
    params: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Context:
    source: Source
    validator_ran: bool  # the official validator checked the arithmetic and the BR rules already
    validator_terms: frozenset[str] = frozenset()  # business terms the validator already reported
    pdf_text: str | None = None  # ZUGFeRD: text layer of the visible PDF
    duplicate_of: str | None = (
        None  # id of another document with the same seller and invoice number
    )


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _differs(a: Decimal, b: Decimal) -> bool:
    return abs(_money(a) - _money(b)) > CENT


# --- profile, amounts, currency -------------------------------------------------------------


def check_profile(invoice: InvoiceModel) -> list[CheckFinding]:
    spec = (invoice.specification_id or "").lower().replace("-", "").replace("_", "")
    if any(profile in spec for profile in NOT_AN_E_INVOICE_PROFILES):
        return [CheckFinding("BF-NOT-AN-E-INVOICE", "warning", ("BT-24",))]
    return []


def is_small_amount(invoice: InvoiceModel) -> bool:
    gross = invoice.totals.gross
    return invoice.currency == "EUR" and gross is not None and gross <= SMALL_AMOUNT_LIMIT


def check_amount_and_currency(invoice: InvoiceModel) -> list[CheckFinding]:
    findings = []
    if is_small_amount(invoice):
        findings.append(CheckFinding("BF-SMALL-AMOUNT", "info", ("BT-112",)))
    if invoice.currency and invoice.currency != "EUR":
        findings.append(
            CheckFinding("BF-FOREIGN-CURRENCY", "info", ("BT-5",), {"currency": invoice.currency})
        )
    return findings


def check_vat_rates(invoice: InvoiceModel) -> list[CheckFinding]:
    if invoice.seller.address.country_code != "DE":
        return []
    return [
        CheckFinding(
            "BF-VAT-RATE-UNUSUAL", "warning", ("BT-119",), {"rate": f"{v.rate.normalize():f}"}
        )
        for v in invoice.vat_breakdown
        if v.category == "S" and v.rate is not None and v.rate not in GERMAN_STANDARD_RATES
    ]


# --- arithmetic (only when the validator didn't run, e.g. LLM-read documents from M2b) ---------


def check_arithmetic(invoice: InvoiceModel) -> list[CheckFinding]:
    findings = []
    for vat in invoice.vat_breakdown:
        if vat.rate is None or vat.taxable_amount is None or vat.tax_amount is None:
            continue
        expected = _money(vat.taxable_amount * vat.rate / 100)
        if _differs(expected, vat.tax_amount):
            findings.append(
                CheckFinding(
                    "BF-VAT-AMOUNT",
                    "error",
                    ("BT-117",),
                    {
                        "rate": f"{vat.rate.normalize():f}",
                        "expected": f"{expected}",
                        "actual": f"{vat.tax_amount}",
                    },
                )
            )
    totals = invoice.totals
    if totals.net is not None and totals.vat is not None and totals.gross is not None:
        expected = totals.net + totals.vat
        if _differs(expected, totals.gross):
            findings.append(
                CheckFinding(
                    "BF-TOTAL-GROSS",
                    "error",
                    ("BT-112",),
                    {"expected": f"{_money(expected)}", "actual": f"{totals.gross}"},
                )
            )
    amounts = [line.net_amount for line in invoice.lines]
    if totals.line_net is not None and amounts and all(a is not None for a in amounts):
        expected = sum((a for a in amounts if a is not None), Decimal(0))
        if _differs(expected, totals.line_net):
            findings.append(
                CheckFinding(
                    "BF-TOTAL-LINES",
                    "error",
                    ("BT-106",),
                    {"expected": f"{_money(expected)}", "actual": f"{totals.line_net}"},
                )
            )
    return findings


# --- mandatory details -----------------------------------------------------------------------


def _missing_details(invoice: InvoiceModel) -> dict[str, tuple[str, ...]]:
    """Finding code -> business terms, for every § 14 Abs. 4 UStG detail that is missing."""
    seller, buyer = invoice.seller, invoice.buyer
    has_items = bool(invoice.lines) and all(
        line.name and line.quantity is not None for line in invoice.lines
    )
    has_delivery = (
        invoice.delivery_date is not None
        or invoice.period_start is not None
        or invoice.tax_point_date is not None
        or any(line.period_start is not None for line in invoice.lines)
    )
    has_vat = bool(invoice.vat_breakdown) and all(
        v.rate is not None or v.exemption_reason or v.exemption_code for v in invoice.vat_breakdown
    )
    checks = {
        "BF-MISSING-SELLER-NAME": (bool(seller.name), ("BT-27",)),
        "BF-MISSING-SELLER-ADDRESS": (
            bool(seller.address.line1 and seller.address.city and seller.address.post_code),
            ("BT-35", "BT-37", "BT-38"),
        ),
        "BF-MISSING-BUYER-NAME": (bool(buyer.name), ("BT-44",)),
        "BF-MISSING-BUYER-ADDRESS": (
            bool(buyer.address.line1 and buyer.address.city and buyer.address.post_code),
            ("BT-50", "BT-52", "BT-53"),
        ),
        "BF-MISSING-TAX-ID": (bool(seller.vat_id or seller.tax_number), ("BT-31", "BT-32")),
        "BF-MISSING-ISSUE-DATE": (invoice.issue_date is not None, ("BT-2",)),
        "BF-MISSING-NUMBER": (bool(invoice.number), ("BT-1",)),
        "BF-MISSING-ITEMS": (has_items, ("BT-129", "BT-153")),
        "BF-MISSING-DELIVERY-DATE": (has_delivery, ("BT-72", "BT-73", "BT-74")),
        "BF-MISSING-VAT": (has_vat, ("BT-119", "BT-120")),
    }
    return {detail: terms for detail, (present, terms) in checks.items() if not present}


# § 33 UStDV: a small-amount invoice needs only these details.
SMALL_AMOUNT_DETAILS = {
    "BF-MISSING-SELLER-NAME",
    "BF-MISSING-SELLER-ADDRESS",
    "BF-MISSING-ISSUE-DATE",
    "BF-MISSING-ITEMS",
    "BF-MISSING-VAT",
}


def check_mandatory_details(invoice: InvoiceModel, context: Context) -> list[CheckFinding]:
    missing = _missing_details(invoice)
    if is_small_amount(invoice):
        missing = {c: t for c, t in missing.items() if c in SMALL_AMOUNT_DETAILS}
    return [
        CheckFinding(code, "warning", terms)
        for code, terms in missing.items()
        if not context.validator_terms.intersection(terms)
    ]


# --- PDF vs. XML (ZUGFeRD: the XML is legally leading, F15) ------------------------------------

_SPACES = re.compile(r"\s+")


def normalise_text(text: str) -> str:
    return _SPACES.sub("", text).lower()


def amount_spellings(value: Decimal) -> set[str]:
    """How an amount may appear in a PDF: 1234.56, 1234,56, 1.234,56, 1,234.56."""
    whole, cents = f"{abs(_money(value)):.2f}".split(".")
    grouped = f"{int(whole):,}"
    return {
        f"{whole}.{cents}",
        f"{whole},{cents}",
        f"{grouped.replace(',', '.')},{cents}",
        f"{grouped}.{cents}",
    }


def check_pdf_matches_xml(invoice: InvoiceModel, pdf_text: str) -> list[CheckFinding]:
    text = normalise_text(pdf_text)
    if not text:
        return [CheckFinding("BF-PDF-NO-TEXT", "info")]
    findings = []
    if invoice.number and normalise_text(invoice.number) not in text:
        findings.append(
            CheckFinding(
                "BF-PDF-XML-MISMATCH-NUMBER", "warning", ("BT-1",), {"number": invoice.number}
            )
        )
    gross = invoice.totals.gross
    if gross is not None and not any(s in text for s in amount_spellings(gross)):
        findings.append(
            CheckFinding(
                "BF-PDF-XML-MISMATCH-TOTAL", "warning", ("BT-112",), {"amount": f"{_money(gross)}"}
            )
        )
    return findings


# --- all checks ------------------------------------------------------------------------------


def check_invoice(invoice: InvoiceModel, context: Context) -> list[CheckFinding]:
    findings = (
        check_profile(invoice) + check_amount_and_currency(invoice) + check_vat_rates(invoice)
    )
    if not context.validator_ran:
        findings += check_arithmetic(invoice)
    findings += check_mandatory_details(invoice, context)
    if context.source is Source.ZUGFERD and context.pdf_text is not None:
        findings += check_pdf_matches_xml(invoice, context.pdf_text)
    if context.duplicate_of:
        findings.append(
            CheckFinding(
                "BF-DUPLICATE", "warning", ("BT-1", "BT-27"), {"document_id": context.duplicate_of}
            )
        )
    return findings
