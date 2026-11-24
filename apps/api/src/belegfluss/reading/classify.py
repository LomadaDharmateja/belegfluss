"""Decide what a document is, from its content, and get the invoice XML out of it.

All input is untrusted. XML is parsed without network access or entity resolution, and documents
with a DOCTYPE are rejected: e-invoices never need one (ADR-0014).
"""

import io
from dataclasses import dataclass
from enum import StrEnum

import pypdfium2 as pdfium
from lxml import etree
from pypdf import PdfReader
from pypdf.errors import PdfReadError

UBL_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
UBL_CREDIT_NOTE = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
CII = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"

# File names under which ZUGFeRD / Factur-X / XRechnung embed the invoice XML in a PDF/A-3.
EMBEDDED_XML_NAMES = {"factur-x.xml", "zugferd-invoice.xml", "xrechnung.xml"}


class Syntax(StrEnum):
    UBL_INVOICE = "ubl-invoice"
    UBL_CREDIT_NOTE = "ubl-creditnote"
    CII = "cii"


class Source(StrEnum):
    XML = "xml"  # an XML e-invoice file
    ZUGFERD = "zugferd"  # PDF with the invoice XML embedded
    UNSTRUCTURED = "unstructured"  # PDF or image without structured data (read by an LLM from M2b)


class ReadingError(Exception):
    """The document can't be read. `code` is a stable finding code shown to the user."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Classified:
    source: Source
    syntax: Syntax | None = None
    xml: bytes | None = None
    pdf_text: str | None = None


_PARSER = etree.XMLParser(
    resolve_entities=False, no_network=True, load_dtd=False, dtd_validation=False, huge_tree=False
)


def parse_untrusted_xml(data: bytes) -> etree._Element:
    try:
        root = etree.fromstring(data, _PARSER)
    except etree.XMLSyntaxError as exc:
        raise ReadingError("BF-XML-UNREADABLE") from exc
    # `doctype` exists at runtime but is missing from lxml-stubs.
    if getattr(root.getroottree().docinfo, "doctype", ""):
        raise ReadingError("BF-XML-DOCTYPE")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReadingError("BF-XML-ENCODING") from exc
    return root


def syntax_of(root: etree._Element) -> Syntax | None:
    name = etree.QName(root)
    if name.namespace == UBL_INVOICE and name.localname == "Invoice":
        return Syntax.UBL_INVOICE
    if name.namespace == UBL_CREDIT_NOTE and name.localname == "CreditNote":
        return Syntax.UBL_CREDIT_NOTE
    if name.namespace == CII and name.localname == "CrossIndustryInvoice":
        return Syntax.CII
    return None


def embedded_invoice_xml(pdf: bytes) -> bytes | None:
    try:
        reader = PdfReader(io.BytesIO(pdf))
        if reader.is_encrypted:
            raise ReadingError("BF-PDF-ENCRYPTED")
        attachments = reader.attachments
    except (PdfReadError, ValueError, KeyError) as exc:
        raise ReadingError("BF-PDF-UNREADABLE") from exc
    for name, contents in attachments.items():
        if name.lower() in EMBEDDED_XML_NAMES and contents:
            return contents[0]
    return None


def pdf_text(pdf: bytes, max_pages: int) -> str:
    """Text layer of the first `max_pages` pages ('' for scans without text)."""
    try:
        document = pdfium.PdfDocument(pdf)
    except pdfium.PdfiumError as exc:
        raise ReadingError("BF-PDF-UNREADABLE") from exc
    try:
        parts = []
        for index in range(min(len(document), max_pages)):
            page = document[index]
            textpage = page.get_textpage()
            parts.append(textpage.get_text_range())
            textpage.close()
            page.close()
        return "\n".join(parts)
    finally:
        document.close()


def classify(data: bytes, media_type: str, *, max_pdf_pages: int) -> Classified:
    if media_type == "application/xml":
        syntax = syntax_of(parse_untrusted_xml(data))
        if syntax is None:
            raise ReadingError("BF-NOT-AN-INVOICE")
        return Classified(source=Source.XML, syntax=syntax, xml=data)

    if media_type == "application/pdf":
        xml = embedded_invoice_xml(data)
        if xml is None:
            return Classified(source=Source.UNSTRUCTURED)
        syntax = syntax_of(parse_untrusted_xml(xml))
        if syntax is None:
            raise ReadingError("BF-NOT-AN-INVOICE")
        return Classified(
            source=Source.ZUGFERD, syntax=syntax, xml=xml, pdf_text=pdf_text(data, max_pdf_pages)
        )

    return Classified(source=Source.UNSTRUCTURED)
