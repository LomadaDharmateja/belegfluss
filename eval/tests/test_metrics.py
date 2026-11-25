from datetime import date
from decimal import Decimal

import pytest
from belegfluss.reading import InvoiceModel
from belegfluss.reading.model import Party, Totals, VatBreakdown

from belegfluss_eval.metrics import FIELDS, Scored, compare, summarise, wilson


def model(**changes: object) -> InvoiceModel:
    base = InvoiceModel(
        number="RE-2026-0042",
        issue_date=date(2026, 11, 18),
        currency="EUR",
        seller=Party(name="Malerbetrieb Groß & Söhne", vat_id="DE123456789"),
        ibans=["DE02100100100006820101"],
        totals=Totals(net=Decimal("1234.00"), vat=Decimal("234.46"), gross=Decimal("1468.46")),
        vat_breakdown=[VatBreakdown(rate=Decimal(19), tax_amount=Decimal("234.46"))],
    )
    return base.model_copy(update=changes)


def test_same_values_in_another_notation_are_equal() -> None:
    label = model()
    read = model(
        number=" re-2026-0042 ",
        currency="eur",
        seller=Party(
            name="Malerbetrieb  GROSS".replace("GROSS", "Groß") + " & Söhne",
            vat_id="DE 123 456 789",
        ),
        ibans=["DE02 1001 0010 0006 8201 01"],
        totals=Totals(net=Decimal("1234"), vat=Decimal("234.460"), gross=Decimal("1468.46")),
        vat_breakdown=[VatBreakdown(rate=Decimal("19.00"), tax_amount=Decimal("234.46"))],
    )
    assert all(compare(label, read).values())


@pytest.mark.parametrize(
    ("field", "changes"),
    [
        ("number", {"number": "RE-2026-0043"}),
        (
            "gross",
            {
                "totals": Totals(
                    net=Decimal("1234.00"), vat=Decimal("234.46"), gross=Decimal("1468.47")
                )
            },
        ),
        ("seller_name", {"seller": Party(name="Malerbetrieb Gross & Söhne", vat_id="DE123456789")}),
        (
            "vat_breakdown",
            {"vat_breakdown": [VatBreakdown(rate=Decimal(7), tax_amount=Decimal("234.46"))]},
        ),
        ("due_date", {"due_date": date(2026, 12, 2)}),  # invented: the label has no due date
    ],
)
def test_each_difference_is_counted_on_its_field_only(
    field: str, changes: dict[str, object]
) -> None:
    result = compare(model(), model(**changes))
    assert [name for name in FIELDS if not result[name]] == [field]


def test_wilson_interval() -> None:
    low, high = wilson(8, 10)
    assert (round(low, 3), round(high, 3)) == (0.490, 0.943)
    assert wilson(0, 0) == (0.0, 1.0)
    assert wilson(10, 10)[1] == 1.0


def scored(doc_id: str, correct: bool, flagged: bool, seconds: float) -> Scored:
    fields = {name: True for name in FIELDS}
    fields["gross"] = correct
    return Scored(doc_id, "synthetic/original", fields, flagged, 0.004, seconds)


def test_summary_rates() -> None:
    summary = summarise(
        [
            scored("a", correct=True, flagged=False, seconds=2),
            scored("b", correct=True, flagged=True, seconds=3),  # false alarm
            scored("c", correct=False, flagged=True, seconds=4),  # caught
            scored("d", correct=False, flagged=False, seconds=9),  # missed
        ]
    )
    assert summary.documents == 4
    assert summary.document_accuracy == 0.5
    assert summary.field_accuracy["gross"] == 0.5
    assert summary.field_accuracy["number"] == 1.0
    assert summary.catch_rate == 0.5
    assert summary.false_alarm_rate == 0.5
    assert summary.cost_per_document_usd == pytest.approx(0.004)
    assert summary.seconds_p50 == 3.5
