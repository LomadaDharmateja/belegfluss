"""Turn the KoSIT 'xr' intermediate XML into our InvoiceModel, by business-term ID (xr:id).

The xr XML is produced by the official transform from already-checked input, so it is parsed
normally. Values that don't parse (a malformed date or amount) become None: the validator and the
checks report the problem.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from lxml import etree

from belegfluss.reading.model import (
    Address,
    InvoiceModel,
    Line,
    Party,
    Totals,
    VatBreakdown,
)

XR_ID = "{urn:ce.eu:en16931:2017:xoev-de:kosit:standard:xrechnung-1}id"


def _child(element: etree._Element | None, term: str) -> etree._Element | None:
    if element is None:
        return None
    for child in element:
        if child.get(XR_ID) == term:
            return child
    return None


def _children(element: etree._Element | None, term: str) -> list[etree._Element]:
    if element is None:
        return []
    return [child for child in element if child.get(XR_ID) == term]


def _text(element: etree._Element | None, term: str) -> str | None:
    child = _child(element, term)
    if child is None or child.text is None:
        return None
    value = child.text.strip()
    return value or None


def _amount(element: etree._Element | None, term: str) -> Decimal | None:
    value = _text(element, term)
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _date(element: etree._Element | None, term: str) -> date | None:
    value = _text(element, term)
    if value is None:
        return None
    try:
        if len(value) == 8 and value.isdigit():  # CII format 102: YYYYMMDD
            return date(int(value[:4]), int(value[4:6]), int(value[6:]))
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _address(
    group: etree._Element | None, line1: str, line2: str, city: str, post: str, country: str
) -> Address:
    return Address(
        line1=_text(group, line1),
        line2=_text(group, line2),
        city=_text(group, city),
        post_code=_text(group, post),
        country_code=_text(group, country),
    )


def _line(group: etree._Element) -> Line:
    period = _child(group, "BG-26")
    return Line(
        id=_text(group, "BT-126"),
        name=_text(_child(group, "BG-31"), "BT-153"),
        quantity=_amount(group, "BT-129"),
        unit=_text(group, "BT-130"),
        net_amount=_amount(group, "BT-131"),
        unit_price=_amount(_child(group, "BG-29"), "BT-146"),
        vat_category=_text(_child(group, "BG-30"), "BT-151"),
        vat_rate=_amount(_child(group, "BG-30"), "BT-152"),
        period_start=_date(period, "BT-134"),
        period_end=_date(period, "BT-135"),
    )


def read_xr(xr: bytes) -> InvoiceModel:
    root = etree.fromstring(xr)
    seller = _child(root, "BG-4")
    buyer = _child(root, "BG-7")
    totals = _child(root, "BG-22")
    payment = _child(root, "BG-16")
    return InvoiceModel(
        number=_text(root, "BT-1"),
        issue_date=_date(root, "BT-2"),
        type_code=_text(root, "BT-3"),
        currency=_text(root, "BT-5"),
        vat_currency=_text(root, "BT-6"),
        tax_point_date=_date(root, "BT-7"),
        due_date=_date(root, "BT-9"),
        buyer_reference=_text(root, "BT-10"),
        payment_terms=_text(root, "BT-20"),
        specification_id=_text(_child(root, "BG-2"), "BT-24"),
        seller=Party(
            name=_text(seller, "BT-27"),
            vat_id=_text(seller, "BT-31"),
            tax_number=_text(seller, "BT-32"),
            address=_address(_child(seller, "BG-5"), "BT-35", "BT-36", "BT-37", "BT-38", "BT-40"),
        ),
        buyer=Party(
            name=_text(buyer, "BT-44"),
            vat_id=_text(buyer, "BT-48"),
            address=_address(_child(buyer, "BG-8"), "BT-50", "BT-51", "BT-52", "BT-53", "BT-55"),
        ),
        delivery_date=_date(_child(root, "BG-13"), "BT-72"),
        period_start=_date(_child(root, "BG-14"), "BT-73"),
        period_end=_date(_child(root, "BG-14"), "BT-74"),
        ibans=[
            iban
            for transfer in _children(payment, "BG-17")
            if (iban := _text(transfer, "BT-84")) is not None
        ],
        totals=Totals(
            line_net=_amount(totals, "BT-106"),
            allowances=_amount(totals, "BT-107"),
            charges=_amount(totals, "BT-108"),
            net=_amount(totals, "BT-109"),
            vat=_amount(totals, "BT-110"),
            vat_in_accounting_currency=_amount(totals, "BT-111"),
            gross=_amount(totals, "BT-112"),
            paid=_amount(totals, "BT-113"),
            rounding=_amount(totals, "BT-114"),
            due=_amount(totals, "BT-115"),
        ),
        vat_breakdown=[
            VatBreakdown(
                category=_text(group, "BT-118"),
                rate=_amount(group, "BT-119"),
                taxable_amount=_amount(group, "BT-116"),
                tax_amount=_amount(group, "BT-117"),
                exemption_reason=_text(group, "BT-120"),
                exemption_code=_text(group, "BT-121"),
            )
            for group in _children(root, "BG-23")
        ],
        lines=[_line(group) for group in _children(root, "BG-25")],
    )
