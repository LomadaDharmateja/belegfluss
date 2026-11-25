from datetime import date
from decimal import Decimal

import pytest
from belegfluss.reading import InvoiceModel
from belegfluss.reading.model import Party, Totals, VatBreakdown

from belegfluss_eval.metrics import FIELDS, Scored, agreement, compare, summarise, wilson


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


def test_two_runs_on_the_same_documents_show_which_changed_result() -> None:
    # A live model isn't deterministic: the same prompt on the same documents can differ per run.
    first = [scored(d, bool(ok), False, 1) for d, ok in zip("abcd", [1, 1, 0, 0], strict=True)]
    second = [scored(d, bool(ok), False, 1) for d, ok in zip("abcd", [1, 0, 1, 0], strict=True)]
    result = agreement(first, second)
    assert (result.right_in_both, result.wrong_in_both) == (1, 1)
    assert result.right_only_in_first == ["b"]
    assert result.right_only_in_second == ["c"]
    with pytest.raises(ValueError, match="different documents"):
        agreement(first, second[:3])


def test_no_vat_written_as_zero_or_left_out_is_the_same() -> None:
    label = model(
        totals=Totals(net=Decimal("100.00"), vat=None, gross=Decimal("100.00")),
        vat_breakdown=[],
    )
    read = model(
        totals=Totals(net=Decimal("100.00"), vat=Decimal("0.00"), gross=Decimal("100.00")),
        vat_breakdown=[VatBreakdown(rate=Decimal(0), tax_amount=Decimal("0.00"))],
    )
    assert all(compare(label, read).values())


def test_line_count_does_not_decide_document_accuracy() -> None:
    fields = {name: True for name in FIELDS}
    fields["line_count"] = False
    assert Scored("a", "official/original", fields, False, 0.0, 1.0).correct


def test_placeholders_of_the_official_test_files_count_as_empty() -> None:
    label = model(seller=Party(name="[Seller name]", vat_id="DE123456789"))
    assert compare(label, model(seller=Party(name=None, vat_id="DE123456789")))["seller_name"]
    assert not compare(label, model(seller=Party(name="Real GmbH", vat_id="DE123456789")))[
        "seller_name"
    ]


def test_document_intelligence_mapping_gets_the_same_rules() -> None:
    from belegfluss_eval.scoring import read_di

    model = read_di(
        {
            "InvoiceId": "RE-1",
            "InvoiceTotal": {"amount": 119.0, "currency": "EUR"},
            "AmountDue": None,
            "TaxDetails": [
                {"Amount": {"amount": 19.0, "currency": "EUR"}},
                {"Amount": {"amount": 19.0, "currency": "EUR"}, "Rate": "19,00%"},
            ],
        }
    )
    assert model is not None
    assert model.totals.due == Decimal("119.00")
    assert [(v.rate, v.tax_amount) for v in model.vat_breakdown] == [
        (Decimal("19.00"), Decimal("19.00"))
    ]
