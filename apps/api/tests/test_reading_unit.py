"""Classification, untrusted-input handling, ZUGFeRD extraction and reading of our own fixtures."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from belegfluss.reading import ReadingError, Source, Syntax, classify, read_invoice
from tests.pdfs import encrypted_pdf, text_pdf, zugferd_pdf

FIXTURES = Path(__file__).parent / "fixtures"
CII = (FIXTURES / "invoice_cii.xml").read_bytes()
CREDIT_NOTE = (FIXTURES / "creditnote_ubl.xml").read_bytes()


def test_cii_fixture_is_read() -> None:
    invoice = read_invoice(CII, Syntax.CII)
    assert invoice.number == "RE-2026-1107"
    assert invoice.issue_date == date(2026, 11, 18)
    assert invoice.delivery_date == date(2026, 11, 15)
    assert invoice.due_date == date(2026, 12, 2)
    assert invoice.seller.name == "Haustechnik Schäfer GmbH"
    assert invoice.seller.address.city == "Nürnberg"
    assert invoice.seller.vat_id == "DE987654321"
    assert invoice.buyer.name == "Freiberufler Jana Beispiel"
    assert invoice.ibans == ["DE02100100100006820101"]
    assert invoice.totals.gross == Decimal("447.40")
    assert [(v.rate, v.taxable_amount, v.tax_amount) for v in invoice.vat_breakdown] == [
        (Decimal(19), Decimal("340.00"), Decimal("64.60")),
        (Decimal(7), Decimal("40.00"), Decimal("2.80")),
    ]
    assert [line.name for line in invoice.lines] == [
        "Reparatur Heizungsanlage (Arbeitszeit)",
        "Fachbuch „Wärmepumpen“",
    ]
    assert invoice.lines[0].quantity == Decimal(4)


def test_ubl_credit_note_is_read() -> None:
    classified = classify(CREDIT_NOTE, "application/xml", max_pdf_pages=5)
    assert classified.syntax is Syntax.UBL_CREDIT_NOTE
    invoice = read_invoice(CREDIT_NOTE, Syntax.UBL_CREDIT_NOTE)
    assert invoice.number == "GS-2026-0042"
    assert invoice.type_code == "381"
    assert invoice.seller.name == "Grünwald Werkstatt GmbH"
    assert invoice.seller.address.city == "Würzburg"
    assert invoice.totals.due == Decimal("119.00")
    assert invoice.lines[0].name == "Gutschrift für Ölfilter (Rücksendung)"
    assert invoice.lines[0].quantity == Decimal(2)


# --- untrusted XML -----------------------------------------------------------------------------

BILLION_LAUGHS = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">&lol2;</Invoice>"""

LATIN_1 = (
    '<?xml version="1.0" encoding="ISO-8859-1"?>'
    '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">Müller</Invoice>'
).encode("latin-1")

EXTERNAL_ENTITY = b"""<?xml version="1.0"?>
<!DOCTYPE x [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">&xxe;</Invoice>"""


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (BILLION_LAUGHS, "BF-XML-DOCTYPE"),
        (EXTERNAL_ENTITY, "BF-XML-DOCTYPE"),
        (b"<Invoice><unclosed></Invoice>", "BF-XML-UNREADABLE"),
        (b"<note><to>someone</to></note>", "BF-NOT-AN-INVOICE"),
        (LATIN_1, "BF-XML-ENCODING"),
    ],
    ids=["billion-laughs", "external-entity", "malformed", "not-an-invoice", "latin-1"],
)
def test_untrusted_xml_is_rejected_with_a_code(data: bytes, code: str) -> None:
    with pytest.raises(ReadingError) as caught:
        classify(data, "application/xml", max_pdf_pages=5)
    assert caught.value.code == code


# --- PDFs and images ---------------------------------------------------------------------------


def test_pdf_without_embedded_xml_is_unstructured() -> None:
    classified = classify(
        text_pdf(["Rechnung 123", "Summe 10,00 EUR"]), "application/pdf", max_pdf_pages=5
    )
    assert classified.source is Source.UNSTRUCTURED


def test_image_is_unstructured() -> None:
    classified = classify(b"\x89PNG\r\n\x1a\n" + b"\0" * 32, "image/png", max_pdf_pages=5)
    assert classified.source is Source.UNSTRUCTURED


def test_zugferd_pdf_yields_embedded_xml_and_text() -> None:
    pdf = zugferd_pdf(
        CII, ["Haustechnik Schaefer GmbH", "Rechnung RE-2026-1107", "Gesamt 447,40 EUR"]
    )
    classified = classify(pdf, "application/pdf", max_pdf_pages=5)
    assert classified.source is Source.ZUGFERD
    assert classified.syntax is Syntax.CII
    assert classified.xml is not None
    assert read_invoice(classified.xml, Syntax.CII).number == "RE-2026-1107"
    assert classified.pdf_text is not None
    assert "RE-2026-1107" in classified.pdf_text
    assert "447,40" in classified.pdf_text


def test_broken_pdf_is_rejected_with_a_code() -> None:
    with pytest.raises(ReadingError) as caught:
        classify(b"%PDF-1.7\nthis is not a real pdf", "application/pdf", max_pdf_pages=5)
    assert caught.value.code == "BF-PDF-UNREADABLE"


# Regression: a real receipt was "encrypted" with an empty password (permissions only) and was
# wrongly reported as unreadable (seen in the first M2a run on real data).
def test_pdf_encrypted_with_empty_password_is_read() -> None:
    visible = ["Rechnung RE-2026-1107", "Summe 447,40 EUR"]
    pdf = encrypted_pdf(zugferd_pdf(CII, visible), user_password="")
    classified = classify(pdf, "application/pdf", max_pdf_pages=5)
    assert classified.source is Source.ZUGFERD
    assert classified.pdf_text is not None and "RE-2026-1107" in classified.pdf_text


def test_pdf_that_needs_a_password_is_reported() -> None:
    pdf = encrypted_pdf(text_pdf(["Rechnung 1"]), user_password="secret")
    with pytest.raises(ReadingError) as caught:
        classify(pdf, "application/pdf", max_pdf_pages=5)
    assert caught.value.code == "BF-PDF-ENCRYPTED"
