"""Synthetic part of the set: fictional invoices from a seeded generator (ADR-0018).

The amounts are computed with Decimal like a real invoicing tool (VAT per rate on the sum of the
lines, half-up to the cent), and the labels are exactly what the template prints. Some cases are
deliberately hard: payment terms without a date (the model must not compute one), partial payments,
"no VAT" written in different ways, and documents longer than the 3-page reading limit.
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from belegfluss.reading import InvoiceModel
from belegfluss.reading.model import Address, Line, Party, Totals, VatBreakdown
from faker import Faker
from jinja2 import Environment, FileSystemLoader, select_autoescape

from belegfluss_eval.paths import TEMPLATES

SEED = 20261125
CENT = Decimal("0.01")

# (template, case) in a fixed order; the generator cycles through it.
PLAN = [
    ("letter-de", "standard"),
    ("handwerk-de", "standard"),
    ("freelancer-en", "standard"),
    ("receipt-de", "mixed-rates"),
    ("letter-de", "mixed-rates"),
    ("handwerk-de", "partial-payment"),
    ("freelancer-en", "foreign-currency"),
    ("receipt-de", "small-amount"),
    ("letter-de", "reverse-charge"),
    ("handwerk-de", "terms-only"),
    ("freelancer-en", "terms-only"),
    ("receipt-de", "mixed-rates"),
    ("letter-de", "kleinunternehmer"),
    ("handwerk-de", "skonto"),
    ("freelancer-en", "standard"),
    ("receipt-de", "small-amount"),
    ("letter-de", "credit-note"),
    ("handwerk-de", "standard"),
    ("freelancer-en", "reverse-charge"),
    ("letter-de", "standard"),
]
LONG = {
    "letter-de": 48,
    "handwerk-de": 110,
}  # line counts for the multi-page cases (3 and >3 pages)


@dataclass
class Synthetic:
    doc_id: str
    template: str
    case: str
    labels: InvoiceModel
    html: str
    receipt: bool = False
    notes: list[str] = field(default_factory=list)


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _format_amount(value: Decimal, lang: str) -> str:
    text = f"{value:,.2f}"  # 1,234.56
    if lang == "de":
        text = text.replace(",", "_").replace(".", ",").replace("_", ".")
    return text


def _format_date(day: date, lang: str) -> str:
    return day.strftime("%d.%m.%Y") if lang == "de" else day.strftime("%d %B %Y")


Items = list[tuple[str, str, tuple[float, float]]]

ITEMS_DE: Items = [
    ("Beratung (Stunden)", "Std.", (60, 140)),
    ("Montage Heizkörper", "Stk.", (80, 260)),
    ("Kupferrohr 15 mm", "m", (4, 18)),
    ("Fliesenarbeiten Bad", "m²", (35, 90)),
    ("Anfahrtspauschale", "pausch.", (25, 60)),
    ("Wartung Gasbrennwerttherme", "pausch.", (120, 240)),
    ("Malerarbeiten Wohnzimmer", "m²", (8, 22)),
    ("Webdesign Startseite", "pausch.", (400, 1600)),
    ("Übersetzung Vertrag DE→EN", "Wort", (0.12, 0.25)),
    ("Fotografie Produktbilder", "Std.", (70, 150)),
]
ITEMS_EN: Items = [
    ("Consulting (hours)", "h", (80, 160)),
    ("UX review of checkout flow", "fixed", (600, 2400)),
    ("Backend development", "h", (75, 140)),
    ("Workshop facilitation", "day", (900, 1600)),
    ("Copywriting landing page", "fixed", (300, 900)),
]
ITEMS_RECEIPT = [
    ("Vollkornbrot", Decimal(7)),
    ("Bio Vollmilch 1 l", Decimal(7)),
    ("Äpfel Elstar 1 kg", Decimal(7)),
    ("Kaffee gemahlen 500 g", Decimal(7)),
    ("Spülmittel", Decimal(19)),
    ("Druckerpapier A4", Decimal(19)),
    ("Batterien AA 4er", Decimal(19)),
    ("Kugelschreiber 3er", Decimal(19)),
    ("Käse Gouda 200 g", Decimal(7)),
    ("Mineralwasser 6x1,5 l", Decimal(19)),
]


def _lines(rng: random.Random, items: list[tuple[str, str, tuple[float, float]]], count: int,
           rates: list[Decimal]) -> list[Line]:  # fmt: skip
    lines = []
    for index in range(count):
        name, unit, (low, high) = items[rng.randrange(len(items))]
        quantity = Decimal(rng.choice([1, 1, 2, 3, 4, 5, 8, 10, 12.5, 20]))
        if unit == "Wort":
            quantity = Decimal(rng.randrange(800, 4000))
        price = _money(Decimal(str(rng.uniform(low, high))))
        lines.append(
            Line(
                id=str(index + 1),
                name=name,
                quantity=quantity,
                unit=unit,
                unit_price=price,
                net_amount=_money(quantity * price),
                vat_rate=rates[index % len(rates)],
            )
        )
    return lines


def _breakdown(lines: list[Line], category: str) -> list[VatBreakdown]:
    per_rate: dict[Decimal, Decimal] = {}
    for line in lines:
        rate, amount = line.vat_rate or Decimal(0), line.net_amount or Decimal(0)
        per_rate[rate] = per_rate.get(rate, Decimal(0)) + amount
    return [
        VatBreakdown(
            category=category if rate == 0 else "S",
            rate=rate,
            taxable_amount=_money(taxable),
            tax_amount=_money(taxable * rate / 100),
        )
        for rate, taxable in sorted(per_rate.items(), reverse=True)
    ]


def _party(fake: Faker, *, company: bool = True, country: str = "DE") -> Party:
    return Party(
        name=fake.company() if company else fake.name(),
        address=Address(
            city=fake.city(),
            post_code=fake.postcode(),
            country_code=country,
        ),
    )


def _invoice(index: int, template: str, case: str) -> tuple[InvoiceModel, dict[str, Any]]:
    """The labels plus the extra text only the template needs (street, notes, terms)."""
    rng = random.Random(SEED + index)  # noqa: S311 (test data, not security)
    fake = Faker("de_DE")
    fake.seed_instance(SEED + index)
    lang = "en" if template == "freelancer-en" else "de"
    issue = date(2026, 1, 5) + timedelta(days=rng.randrange(0, 320))
    extra: dict[str, Any] = {"lang": lang, "notes": []}

    seller = _party(fake)
    seller.vat_id = fake.vat_id()
    seller.tax_number = (
        f"{rng.randrange(10, 99)}/{rng.randrange(100, 999)}/{rng.randrange(10000, 99999)}"
    )
    extra["seller_street"] = fake.street_address()
    extra["seller_phone"] = fake.phone_number()
    buyer = _party(fake, company=rng.random() < 0.6)
    extra["buyer_street"] = fake.street_address()
    if lang == "en":
        english = Faker("en_GB")
        english.seed_instance(SEED + index)
        buyer = _party(english, company=True, country="GB")
        extra["buyer_street"] = "12 Example Street"

    currency = "EUR"
    rates = [Decimal(19)]
    category = "S"
    count = rng.randrange(1, 6)
    if case == "mixed-rates":
        rates = [Decimal(19), Decimal(7)]
    if case == "foreign-currency":
        currency = rng.choice(["USD", "CHF", "GBP"])
        rates, category = [Decimal(0)], "O"
        extra["notes"].append("Not subject to German VAT (place of supply outside Germany).")
    if case == "reverse-charge":
        rates, category = [Decimal(0)], "AE"
        buyer.vat_id = rng.choice(["ATU12345678", "NL123456789B01", "FR12345678901"])
        buyer.address.country_code = buyer.vat_id[:2]
        extra["notes"].append(
            "Reverse charge: VAT to be accounted for by the recipient."
            if lang == "en"
            else "Steuerschuldnerschaft des Leistungsempfängers (Reverse Charge)."
        )
    if case == "kleinunternehmer":
        rates, category = [Decimal(0)], "E"
        seller.vat_id = None
        extra["notes"].append("Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.")
        extra["no_vat_line"] = True
    if case == "long":
        count = LONG[template]

    items = ITEMS_EN if lang == "en" else ITEMS_DE
    lines = _lines(rng, items, count, rates)
    breakdown = _breakdown(lines, category)
    net = sum((v.taxable_amount or Decimal(0) for v in breakdown), Decimal(0))
    vat = sum((v.tax_amount or Decimal(0) for v in breakdown), Decimal(0))
    gross = net + vat
    paid = Decimal(0)
    if case == "partial-payment":
        paid = _money(gross * Decimal(rng.choice(["0.3", "0.4", "0.5"])))
        extra["notes"].append(
            f"Abschlagszahlung vom {_format_date(issue - timedelta(days=30), lang)}"
        )

    due_date: date | None = issue + timedelta(days=rng.choice([14, 30]))
    if case in ("terms-only", "skonto"):
        extra["terms"] = (
            f"Payable within {rng.choice([14, 30])} days of the invoice date."
            if lang == "en"
            else f"Zahlbar innerhalb von {rng.choice([10, 14, 30])} Tagen ohne Abzug."
        )
        if case == "skonto":
            extra["terms"] += " Bei Zahlung innerhalb von 7 Tagen 2 % Skonto."
        due_date = None

    prefix = {"letter-de": "RE-2026-", "handwerk-de": "2026-", "freelancer-en": "INV-"}[template]
    number = f"{prefix}{rng.randrange(10, 9999):04d}"
    if case == "credit-note":
        number = f"GS-2026-{rng.randrange(10, 999):04d}"
        extra["title"] = "Gutschrift"

    labels = InvoiceModel(
        number=number,
        issue_date=issue,
        type_code="381" if case == "credit-note" else "380",
        currency=currency,
        due_date=due_date,
        seller=seller,
        buyer=buyer,
        delivery_date=issue - timedelta(days=rng.randrange(0, 10)),
        ibans=[fake.iban()],
        totals=Totals(
            line_net=net,
            net=net,
            vat=vat,
            gross=gross,
            paid=paid or None,
            due=gross - paid,
        ),
        vat_breakdown=breakdown,
        lines=lines,
    )
    return labels, extra


def _receipt(index: int) -> tuple[InvoiceModel, dict[str, Any]]:
    """A till receipt: prices include VAT, the VAT table per rate is printed at the bottom."""
    rng = random.Random(SEED + index)  # noqa: S311 (test data, not security)
    fake = Faker("de_DE")
    fake.seed_instance(SEED + index)
    issue = date(2026, 1, 5) + timedelta(days=rng.randrange(0, 320))
    small = rng.random() < 0.5
    items = [ITEMS_RECEIPT[rng.randrange(len(ITEMS_RECEIPT))] for _ in range(rng.randrange(3, 9))]
    lines = []
    for position, (name, rate) in enumerate(items, start=1):
        gross_price = _money(Decimal(str(rng.uniform(0.79, 9.99 if small else 45))))
        lines.append(
            Line(
                id=str(position),
                name=name,
                quantity=Decimal(1),
                unit_price=gross_price,
                net_amount=gross_price,
                vat_rate=rate,
            )
        )
    per_rate: dict[Decimal, Decimal] = {}
    for line in lines:
        rate, amount = line.vat_rate or Decimal(0), line.net_amount or Decimal(0)
        per_rate[rate] = per_rate.get(rate, Decimal(0)) + amount
    breakdown = []
    for rate, gross_sum in sorted(per_rate.items(), reverse=True):
        net = _money(gross_sum * 100 / (100 + rate))
        breakdown.append(
            VatBreakdown(category="S", rate=rate, taxable_amount=net, tax_amount=gross_sum - net)
        )
    gross = sum((line.net_amount or Decimal(0) for line in lines), Decimal(0))
    net_total = sum((v.taxable_amount or Decimal(0) for v in breakdown), Decimal(0))
    seller = Party(
        name=f"{fake.last_name()} Markt GmbH",
        vat_id=fake.vat_id(),
        address=Address(city=fake.city(), post_code=fake.postcode(), country_code="DE"),
    )
    labels = InvoiceModel(
        number=str(rng.randrange(1000, 99999)),
        issue_date=issue,
        type_code="380",
        currency="EUR",
        seller=seller,
        totals=Totals(net=net_total, vat=gross - net_total, gross=gross, due=gross),
        vat_breakdown=breakdown,
        lines=lines,
    )
    extra = {
        "lang": "de",
        "seller_street": fake.street_address(),
        "time": f"{rng.randrange(8, 20):02d}:{rng.randrange(0, 60):02d}",
        "terminal": f"Kasse {rng.randrange(1, 9)}",
    }
    return labels, extra


def _context(labels: InvoiceModel, extra: dict[str, Any]) -> dict[str, Any]:
    """Everything formatted for printing, in the document's language."""
    lang = extra["lang"]
    symbol = {"EUR": "€", "USD": "$", "CHF": "CHF", "GBP": "£"}[labels.currency or "EUR"]

    def amount(value: Decimal | None) -> str:
        return _format_amount(value or Decimal(0), lang)

    return {
        "doc": labels,
        "x": extra,
        "symbol": symbol,
        "amount": amount,
        "day": lambda d: _format_date(d, lang) if d else "",
        "qty": lambda q: _format_amount(q, lang).removesuffix(",00").removesuffix(".00"),
    }


def generate(count: int = 80) -> list[Synthetic]:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"])
    )
    result = []
    for index in range(count):
        template, case = PLAN[index % len(PLAN)]
        if index in (count - 4, count - 3):
            template, case = "letter-de", "long"
        if index in (count - 2, count - 1):
            template, case = "handwerk-de", "long"
        if template == "receipt-de":
            labels, extra = _receipt(index)
        else:
            labels, extra = _invoice(index, template, case)
        html = environment.get_template(f"{template}.html.j2").render(**_context(labels, extra))
        result.append(
            Synthetic(
                doc_id=f"synthetic-{index + 1:03d}",
                template=template,
                case=case,
                labels=labels,
                html=html,
                receipt=template == "receipt-de",
            )
        )
    return result


def render(items: list[Synthetic], out: Path) -> dict[str, Path]:
    """HTML -> PDF with headless Chromium (Playwright). A4, or receipt width with its own height."""
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    pdfs = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        for item in items:
            page.set_content(item.html, wait_until="load")
            if item.receipt:
                height_mm = page.evaluate("document.body.scrollHeight") * 25.4 / 96 + 12
                pdf = page.pdf(width="80mm", height=f"{height_mm:.0f}mm", print_background=True)
            else:
                pdf = page.pdf(format="A4", print_background=True, prefer_css_page_size=True)
            path = out / f"{item.doc_id}.pdf"
            path.write_bytes(pdf)
            pdfs[item.doc_id] = path
        browser.close()
    return pdfs
