"""Accountant export (ADR-0009): a ZIP with the approved originals, byte-identical, and summary.csv.

The CSV is for German Excel: UTF-8 with BOM, semicolon separator, comma decimals, dates as
DD.MM.YYYY. Cells from invoices are untrusted: a leading =, +, - or @ is neutralised so a
spreadsheet can't run it as a formula (CSV injection).
"""

import csv
import io
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from belegfluss.models import Document, Invoice
from belegfluss.reading import InvoiceModel

MAX_DOCUMENTS = 500
MAX_BYTES = 200 * 1024 * 1024
EXTENSIONS = {
    "application/pdf": ".pdf",
    "application/xml": ".xml",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}

HEADERS = {
    "de": [
        "Datei",
        "Lieferant",
        "USt-IdNr. Lieferant",
        "Rechnungsnummer",
        "Rechnungsdatum",
        "Fällig am",
        "Währung",
        "Netto 19 %",
        "USt 19 %",
        "Netto 7 %",
        "USt 7 %",
        "Netto sonstige",
        "USt sonstige",
        "Netto gesamt",
        "USt gesamt",
        "Brutto",
        "Zahlbetrag",
        "Format",
        "Profil",
        "Offene Befunde",
    ],
    "en": [
        "File",
        "Supplier",
        "Supplier VAT ID",
        "Invoice number",
        "Invoice date",
        "Due date",
        "Currency",
        "Net 19 %",
        "VAT 19 %",
        "Net 7 %",
        "VAT 7 %",
        "Net other",
        "VAT other",
        "Net total",
        "VAT total",
        "Gross",
        "Amount due",
        "Format",
        "Profile",
        "Open findings",
    ],
}


@dataclass(frozen=True)
class ExportItem:
    document: Document
    invoice: Invoice | None
    open_findings: list[str] = field(default_factory=list)  # codes of error/warning findings


def _decimal(value: Decimal | None) -> str:
    return "" if value is None else f"{value:.2f}".replace(".", ",")


def _date(value: date | None) -> str:
    return "" if value is None else value.strftime("%d.%m.%Y")


def safe_cell(value: str | None) -> str:
    text = (value or "").replace("\r", " ").replace("\n", " ")
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def _rates(model: InvoiceModel) -> dict[str, Decimal]:
    """Net and VAT per German rate (category S), everything else as 'other'."""
    sums = {key: Decimal(0) for key in ("net19", "vat19", "net7", "vat7", "net_other", "vat_other")}
    for vat in model.vat_breakdown:
        rate = vat.rate if vat.category == "S" else None
        key = "19" if rate == Decimal(19) else "7" if rate == Decimal(7) else "_other"
        sums[f"net{key}"] += vat.taxable_amount or Decimal(0)
        sums[f"vat{key}"] += vat.tax_amount or Decimal(0)
    return sums


def file_name(item: ExportItem, taken: set[str]) -> str:
    invoice = item.invoice
    parts = (
        [str(invoice.issue_date or ""), invoice.seller_name or "", invoice.number or ""]
        if invoice
        else [item.document.created_at.date().isoformat(), "beleg", str(item.document.id)[:8]]
    )
    stem = (
        "_".join(re.sub(r"[^\w.-]+", "-", part).strip("-.")[:60] for part in parts if part)
        or "beleg"
    )
    ext = EXTENSIONS.get(item.document.media_type, "")
    name, counter = f"{stem}{ext}", 2
    while name.lower() in taken:
        name, counter = f"{stem}-{counter}{ext}", counter + 1
    taken.add(name.lower())
    return name


def _row(item: ExportItem, name: str) -> list[str]:
    invoice = item.invoice
    if invoice is None:
        return [name] + [""] * 18 + [safe_cell(", ".join(item.open_findings))]
    model = InvoiceModel.model_validate(invoice.model)
    rates = _rates(model)
    return [
        name,
        safe_cell(invoice.seller_name),
        safe_cell(invoice.seller_vat_id),
        safe_cell(invoice.number),
        _date(invoice.issue_date),
        _date(model.due_date),
        safe_cell(invoice.currency),
        *(
            _decimal(rates[key])
            for key in ("net19", "vat19", "net7", "vat7", "net_other", "vat_other")
        ),
        _decimal(invoice.net_total),
        _decimal(invoice.vat_total),
        _decimal(invoice.gross_total),
        _decimal(invoice.amount_due),
        invoice.source,
        safe_cell(invoice.specification_id),
        safe_cell(", ".join(item.open_findings)),
    ]


def build_zip(
    items: list[ExportItem], read_original: Callable[[str], bytes], lang: str = "de"
) -> bytes:
    buffer = io.BytesIO()
    table = io.StringIO()
    writer = csv.writer(table, delimiter=";", lineterminator="\r\n")
    writer.writerow(HEADERS.get(lang, HEADERS["de"]))
    taken = {"summary.csv"}
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in items:
            name = file_name(item, taken)
            archive.writestr(name, read_original(item.document.blob_name))
            writer.writerow(_row(item, name))
        archive.writestr("summary.csv", "﻿" + table.getvalue())
    return buffer.getvalue()
