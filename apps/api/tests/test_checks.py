"""Business checks: each one on our CII fixture with one deliberate change."""

from decimal import Decimal
from pathlib import Path

import pytest

from belegfluss.checks import Context, amount_spellings, check_invoice
from belegfluss.reading import InvoiceModel, Source, Syntax, read_invoice
from belegfluss.reading.model import Address, Line, VatBreakdown

CII = (Path(__file__).parent / "fixtures" / "invoice_cii.xml").read_bytes()
XML = Context(source=Source.XML, validator_ran=True)
NO_VALIDATOR = Context(source=Source.XML, validator_ran=False)


@pytest.fixture
def invoice() -> InvoiceModel:
    return read_invoice(CII, Syntax.CII)


def codes(invoice: InvoiceModel, context: Context = XML) -> list[str]:
    return [f.code for f in check_invoice(invoice, context)]


def test_clean_invoice_has_no_findings(invoice: InvoiceModel) -> None:
    assert codes(invoice) == []
    assert codes(invoice, NO_VALIDATOR) == []


# --- profile, amount, currency, rates ---------------------------------------------------------


@pytest.mark.parametrize("spec", ["urn:factur-x.eu:1p0:minimum", "urn:factur-x.eu:1p0:basicwl"])
def test_minimum_and_basic_wl_are_not_e_invoices(invoice: InvoiceModel, spec: str) -> None:
    assert "BF-NOT-AN-E-INVOICE" in codes(invoice.model_copy(update={"specification_id": spec}))


def test_small_amount_is_noted_and_needs_fewer_details(invoice: InvoiceModel) -> None:
    small = invoice.model_copy(
        update={
            "totals": invoice.totals.model_copy(update={"gross": Decimal("119.00")}),
            "buyer": invoice.buyer.model_copy(update={"name": None}),  # not required up to 250 €
        }
    )
    assert codes(small) == ["BF-SMALL-AMOUNT"]


def test_foreign_currency_is_noted(invoice: InvoiceModel) -> None:
    findings = check_invoice(invoice.model_copy(update={"currency": "CHF"}), XML)
    assert [(f.code, f.params) for f in findings] == [("BF-FOREIGN-CURRENCY", {"currency": "CHF"})]


def test_unusual_german_rate_is_flagged(invoice: InvoiceModel) -> None:
    odd = invoice.model_copy(
        update={"vat_breakdown": [VatBreakdown(category="S", rate=Decimal(16))]}
    )
    findings = [f for f in check_invoice(odd, XML) if f.code == "BF-VAT-RATE-UNUSUAL"]
    assert [f.params for f in findings] == [{"rate": "16"}]


def test_foreign_seller_rates_are_not_judged(invoice: InvoiceModel) -> None:
    austrian = invoice.model_copy(
        update={
            "seller": invoice.seller.model_copy(
                update={
                    "address": Address(line1="x", city="Wien", post_code="1010", country_code="AT")
                }
            ),
            "vat_breakdown": [VatBreakdown(category="S", rate=Decimal(20))],
        }
    )
    assert "BF-VAT-RATE-UNUSUAL" not in codes(austrian)


# --- arithmetic ---------------------------------------------------------------------------------


def test_wrong_vat_amount_is_an_error_when_the_validator_did_not_run(invoice: InvoiceModel) -> None:
    breakdown = [
        invoice.vat_breakdown[0].model_copy(update={"tax_amount": Decimal("60.00")}),
        invoice.vat_breakdown[1],
    ]
    wrong = invoice.model_copy(update={"vat_breakdown": breakdown})
    findings = [f for f in check_invoice(wrong, NO_VALIDATOR) if f.code == "BF-VAT-AMOUNT"]
    assert [(f.severity, f.params) for f in findings] == [
        ("error", {"rate": "19", "expected": "64.60", "actual": "60.00"})
    ]
    assert "BF-VAT-AMOUNT" not in codes(wrong, XML)  # the validator's BR rules cover it


def test_wrong_gross_and_line_sum_are_errors(invoice: InvoiceModel) -> None:
    wrong = invoice.model_copy(
        update={
            "totals": invoice.totals.model_copy(
                update={"gross": Decimal("500.00"), "line_net": Decimal("381.00")}
            )
        }
    )
    assert {"BF-TOTAL-GROSS", "BF-TOTAL-LINES"} <= set(codes(wrong, NO_VALIDATOR))


def test_one_cent_rounding_is_tolerated(invoice: InvoiceModel) -> None:
    off_by_a_cent = invoice.model_copy(
        update={"totals": invoice.totals.model_copy(update={"gross": Decimal("447.41")})}
    )
    assert "BF-TOTAL-GROSS" not in codes(off_by_a_cent, NO_VALIDATOR)


# --- mandatory details ----------------------------------------------------------------------------


def test_missing_details_are_reported(invoice: InvoiceModel) -> None:
    incomplete = invoice.model_copy(
        update={
            "delivery_date": None,
            "seller": invoice.seller.model_copy(update={"vat_id": None}),
            "lines": [Line(name=None, quantity=Decimal(1))],
        }
    )
    assert set(codes(incomplete)) == {
        "BF-MISSING-DELIVERY-DATE",
        "BF-MISSING-TAX-ID",
        "BF-MISSING-ITEMS",
    }


def test_details_the_validator_reported_are_not_repeated(invoice: InvoiceModel) -> None:
    no_number = invoice.model_copy(update={"number": None})
    context = Context(source=Source.XML, validator_ran=True, validator_terms=frozenset({"BT-1"}))
    assert "BF-MISSING-NUMBER" not in codes(no_number, context)
    assert "BF-MISSING-NUMBER" in codes(no_number)


# --- PDF vs XML, duplicates -----------------------------------------------------------------------


def zugferd(text: str) -> Context:
    return Context(source=Source.ZUGFERD, validator_ran=True, pdf_text=text)


def test_pdf_matching_the_xml_has_no_findings(invoice: InvoiceModel) -> None:
    assert codes(invoice, zugferd("Rechnung RE-2026-1107\nGesamtbetrag 447,40 EUR")) == []


def test_pdf_with_other_number_and_total_is_flagged(invoice: InvoiceModel) -> None:
    findings = check_invoice(invoice, zugferd("Rechnung RE-2026-9999\nGesamtbetrag 474,40 EUR"))
    assert [(f.code, f.params) for f in findings] == [
        ("BF-PDF-XML-MISMATCH-NUMBER", {"value": "RE-2026-1107"}),
        ("BF-PDF-XML-MISMATCH-TOTAL", {"value": "447.40"}),
    ]


def test_scanned_pdf_without_text_cannot_be_compared(invoice: InvoiceModel) -> None:
    assert codes(invoice, zugferd("  \n ")) == ["BF-PDF-NO-TEXT"]


def test_amount_spellings_cover_german_and_english() -> None:
    assert amount_spellings(Decimal("1234.5")) == {"1234.50", "1234,50", "1.234,50", "1,234.50"}


def test_duplicate_is_flagged(invoice: InvoiceModel) -> None:
    context = Context(source=Source.XML, validator_ran=True, duplicate_of="abc")
    findings = check_invoice(invoice, context)
    assert [(f.code, f.params) for f in findings] == [("BF-DUPLICATE", {"document_id": "abc"})]
