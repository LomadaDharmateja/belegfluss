"""One invoice model for every input path, named after EN 16931 business terms (BT-n, BG-n).

Every field is optional: invoices can be incomplete or invalid, and the checks and the validator
report what is missing. Amounts are Decimal, never float.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class Address(BaseModel):
    line1: str | None = None  # BT-35 / BT-50
    line2: str | None = None  # BT-36 / BT-51
    city: str | None = None  # BT-37 / BT-52
    post_code: str | None = None  # BT-38 / BT-53
    country_code: str | None = None  # BT-40 / BT-55


class Party(BaseModel):
    name: str | None = None  # BT-27 / BT-44
    vat_id: str | None = None  # BT-31 / BT-48
    tax_number: str | None = None  # BT-32 (seller only)
    address: Address = Field(default_factory=Address)


class VatBreakdown(BaseModel):
    """BG-23: one entry per VAT category and rate."""

    category: str | None = None  # BT-118
    rate: Decimal | None = None  # BT-119
    taxable_amount: Decimal | None = None  # BT-116
    tax_amount: Decimal | None = None  # BT-117
    exemption_reason: str | None = None  # BT-120
    exemption_code: str | None = None  # BT-121


class Line(BaseModel):
    """BG-25."""

    id: str | None = None  # BT-126
    name: str | None = None  # BT-153
    quantity: Decimal | None = None  # BT-129
    unit: str | None = None  # BT-130
    net_amount: Decimal | None = None  # BT-131
    unit_price: Decimal | None = None  # BT-146
    vat_category: str | None = None  # BT-151
    vat_rate: Decimal | None = None  # BT-152
    period_start: date | None = None  # BT-134
    period_end: date | None = None  # BT-135


class Totals(BaseModel):
    """BG-22."""

    line_net: Decimal | None = None  # BT-106
    allowances: Decimal | None = None  # BT-107
    charges: Decimal | None = None  # BT-108
    net: Decimal | None = None  # BT-109
    vat: Decimal | None = None  # BT-110
    vat_in_accounting_currency: Decimal | None = None  # BT-111
    gross: Decimal | None = None  # BT-112
    paid: Decimal | None = None  # BT-113
    rounding: Decimal | None = None  # BT-114
    due: Decimal | None = None  # BT-115


class InvoiceModel(BaseModel):
    number: str | None = None  # BT-1
    issue_date: date | None = None  # BT-2
    type_code: str | None = None  # BT-3 (380 invoice, 381 credit note, ...)
    currency: str | None = None  # BT-5
    vat_currency: str | None = None  # BT-6
    tax_point_date: date | None = None  # BT-7
    due_date: date | None = None  # BT-9
    buyer_reference: str | None = None  # BT-10
    payment_terms: str | None = None  # BT-20
    specification_id: str | None = None  # BT-24 (profile, e.g. XRechnung 3.0 or a ZUGFeRD profile)
    seller: Party = Field(default_factory=Party)  # BG-4
    buyer: Party = Field(default_factory=Party)  # BG-7
    delivery_date: date | None = None  # BT-72
    period_start: date | None = None  # BT-73
    period_end: date | None = None  # BT-74
    ibans: list[str] = Field(default_factory=list)  # BT-84
    totals: Totals = Field(default_factory=Totals)
    vat_breakdown: list[VatBreakdown] = Field(default_factory=list)
    lines: list[Line] = Field(default_factory=list)
