import io
from decimal import Decimal

from belegfluss.checks import Context, check_invoice
from belegfluss.reading import Source
from PIL import Image

from belegfluss_eval.dataset import synthetic, variants


def test_synthetic_labels_add_up() -> None:
    """The labels pass our own arithmetic checks: the printed sums are consistent."""
    for doc in synthetic.generate(80):
        findings = check_invoice(doc.labels, Context(source=Source.AI, validator_ran=False))
        arithmetic = {f.code for f in findings} & {
            "BF-TOTAL-GROSS",
            "BF-TOTAL-LINES",
            "BF-VAT-AMOUNT",
        }
        assert not arithmetic, (doc.doc_id, doc.case, arithmetic)
        totals = doc.labels.totals
        assert totals.net is not None and totals.vat is not None and totals.gross is not None
        assert totals.net + totals.vat == totals.gross
        assert totals.due == totals.gross - (totals.paid or Decimal(0))


def test_generation_is_repeatable_and_covers_every_case() -> None:
    first, second = synthetic.generate(80), synthetic.generate(80)
    assert [d.labels for d in first] == [d.labels for d in second]
    assert {d.case for d in first} >= {
        "standard", "mixed-rates", "partial-payment", "foreign-currency", "small-amount",
        "reverse-charge", "terms-only", "kleinunternehmer", "skonto", "credit-note", "long",
    }  # fmt: skip
    terms_only = [d for d in first if d.case == "terms-only"]
    assert terms_only and all(d.labels.due_date is None for d in terms_only)


def test_variants_are_valid_images() -> None:
    page = io.BytesIO()
    Image.new("RGB", (595, 842), "white").save(page, format="PDF")
    photo = Image.open(io.BytesIO(variants.photo(page.getvalue(), seed=1)))
    assert photo.format == "JPEG" and max(photo.size) <= 2200
    scan = variants.scan(page.getvalue(), seed=1)
    assert scan.startswith(b"%PDF")
