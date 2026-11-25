"""Prepared answers for the fake extractor: our synthetic CII invoice, as a model would read it."""

from belegfluss.extraction.schema import (
    ExtractedInvoice,
    ExtractedLine,
    ExtractedParty,
    ExtractedVat,
)


def good_answer() -> ExtractedInvoice:
    return ExtractedInvoice(
        is_invoice=True,
        number="RE-2026-1107",
        issue_date="2026-11-18",
        due_date="2026-12-02",
        delivery_date="2026-11-15",
        currency="EUR",
        seller=ExtractedParty(
            name="Haustechnik Schäfer GmbH",
            street="Königstraße 7",
            post_code="90402",
            city="Nürnberg",
            country_code="DE",
            vat_id="DE987654321",
            tax_number=None,
        ),
        buyer=ExtractedParty(
            name="Freiberufler Jana Beispiel",
            street="Gartenweg 3",
            post_code="10115",
            city="Berlin",
            country_code="DE",
            vat_id=None,
            tax_number=None,
        ),
        iban="DE02 1001 0010 0006 8201 01",
        lines=[
            ExtractedLine(
                description="Reparatur Heizungsanlage (Arbeitszeit)",
                quantity="4",
                unit_price="85.00",
                net_amount="340.00",
                vat_rate="19",
            ),
            ExtractedLine(
                description="Fachbuch „Wärmepumpen“",
                quantity="1",
                unit_price="40.00",
                net_amount="40.00",
                vat_rate="7",
            ),
        ],
        vat_breakdown=[
            ExtractedVat(rate="19", taxable_amount="340.00", tax_amount="64.60"),
            ExtractedVat(rate="7", taxable_amount="40.00", tax_amount="2.80"),
        ],
        net_total="380.00",
        vat_total="67.40",
        gross_total="447.40",
        amount_due="447.40",
    )


# The visible text of a synthetic plain-PDF invoice with the same content (no embedded XML).
INVOICE_TEXT = [
    "Haustechnik Schäfer GmbH, Königstraße 7, 90402 Nürnberg",
    "USt-IdNr. DE987654321",
    "An: Freiberufler Jana Beispiel, Gartenweg 3, 10115 Berlin",
    "Rechnung RE-2026-1107   Datum 18.11.2026   Leistung 15.11.2026",
    "Reparatur Heizungsanlage (Arbeitszeit)  4 x 85,00  340,00 EUR  19 %",
    "Fachbuch Wärmepumpen  1 x 40,00  40,00 EUR  7 %",
    "Netto 380,00   USt 19 % 64,60   USt 7 % 2,80",
    "Gesamtbetrag 447,40 EUR   zahlbar bis 02.12.2026",
    "IBAN DE02 1001 0010 0006 8201 01",
]
