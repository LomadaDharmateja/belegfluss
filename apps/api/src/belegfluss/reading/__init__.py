"""Reading invoices: classify a document, get the invoice XML, read it into one model (ADR-0014)."""

from belegfluss.reading.classify import Classified, ReadingError, Source, Syntax, classify
from belegfluss.reading.model import InvoiceModel
from belegfluss.reading.transform import to_xr
from belegfluss.reading.xr import read_xr


def read_invoice(xml: bytes, syntax: Syntax) -> InvoiceModel:
    """UBL or CII bytes (already checked by `classify`) -> InvoiceModel."""
    return read_xr(to_xr(xml, syntax))


__all__ = [
    "Classified",
    "InvoiceModel",
    "ReadingError",
    "Source",
    "Syntax",
    "classify",
    "read_invoice",
]
