"""All official XRechnung test-suite files are read, and the key values equal the source XML.

The expected values are read with our own XPaths, independent of the KoSIT transform.
Test data: `python scripts/fetch_test_data.py` (pinned, checksummed, ADR-0008).
"""

import os
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from belegfluss.reading import Source, Syntax, classify, read_invoice

SUITE = Path(__file__).resolve().parents[3] / "testdata/external/xrechnung-testsuite-2026-08-31"
FILES = sorted(p for p in SUITE.rglob("*.xml") if "instances" in p.parts) if SUITE.exists() else []

NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}
_UBL_TOTALS = "/*/cac:LegalMonetaryTotal/cbc:"
_CII_TOTALS = "//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:"
EXPECTED = {
    Syntax.UBL_INVOICE: {
        "number": "/*/cbc:ID",
        "issue_date": "/*/cbc:IssueDate",
        "line_net": _UBL_TOTALS + "LineExtensionAmount",
        "net": _UBL_TOTALS + "TaxExclusiveAmount",
        "vat": "/*/cac:TaxTotal/cbc:TaxAmount[@currencyID = /*/cbc:DocumentCurrencyCode]",
        "gross": _UBL_TOTALS + "TaxInclusiveAmount",
        "due": _UBL_TOTALS + "PayableAmount",
    },
    Syntax.CII: {
        "number": "/rsm:CrossIndustryInvoice/rsm:ExchangedDocument/ram:ID",
        "issue_date": "//rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString",
        "line_net": _CII_TOTALS + "LineTotalAmount",
        "net": _CII_TOTALS + "TaxBasisTotalAmount",
        "vat": _CII_TOTALS + "TaxTotalAmount[@currencyID = //ram:InvoiceCurrencyCode]",
        "gross": _CII_TOTALS + "GrandTotalAmount",
        "due": _CII_TOTALS + "DuePayableAmount",
    },
}


def _value(tree: etree._ElementTree, xpath: str) -> str | None:
    found = tree.xpath(xpath, namespaces=NS)
    return found[0].text.strip() if found else None


def test_suite_is_present() -> None:
    if os.environ.get("CI") and not FILES:
        pytest.fail("Test suite missing in CI: run scripts/fetch_test_data.py")
    if not FILES:
        pytest.skip("Test suite not downloaded: run python scripts/fetch_test_data.py")
    assert len(FILES) == 86


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_official_file_is_read_exactly(path: Path) -> None:
    data = path.read_bytes()

    classified = classify(data, "application/xml", max_pdf_pages=50)
    assert classified.source is Source.XML
    assert classified.syntax in (Syntax.UBL_INVOICE, Syntax.CII)
    assert classified.syntax is not None

    invoice = read_invoice(data, classified.syntax)
    source = etree.parse(str(path))
    paths = EXPECTED[classified.syntax]

    assert invoice.number == _value(source, paths["number"])
    issue_date = _value(source, paths["issue_date"])
    assert issue_date is not None and invoice.issue_date is not None
    assert invoice.issue_date.isoformat().replace("-", "") == issue_date.replace("-", "")
    for field in ("line_net", "net", "vat", "gross", "due"):
        expected = _value(source, paths[field])
        actual = getattr(invoice.totals, field)
        if expected is None:
            assert actual is None, field
        else:
            assert actual == Decimal(expected), field
    assert invoice.lines, "every official case has at least one line"
    assert invoice.seller.name, "every official case names the seller"
