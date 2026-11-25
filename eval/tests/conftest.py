"""A tiny labelled set with recorded answers, written to a temporary eval folder."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from belegfluss.extraction.schema import (
    ExtractedInvoice,
    ExtractedParty,
    ExtractedVat,
    to_invoice_model,
)

from belegfluss_eval import gate, manifest, recording


def answer(**changes: object) -> ExtractedInvoice:
    """A synthetic invoice as the model would return it."""
    base = ExtractedInvoice(
        is_invoice=True,
        number="RE-2026-0042",
        issue_date="2026-11-18",
        due_date="2026-12-02",
        delivery_date=None,
        currency="EUR",
        seller=ExtractedParty(
            name="Malerbetrieb Groß & Söhne",
            street=None,
            post_code=None,
            city=None,
            country_code="DE",
            vat_id="DE123456789",
            tax_number=None,
        ),
        buyer=ExtractedParty(
            name="Studio Beispiel",
            street=None,
            post_code=None,
            city=None,
            country_code=None,
            vat_id=None,
            tax_number=None,
        ),
        iban="DE02 1001 0010 0006 8201 01",
        lines=[],
        vat_breakdown=[ExtractedVat(rate="19", taxable_amount="1234.00", tax_amount="234.46")],
        net_total="1234.00",
        vat_total="234.46",
        gross_total="1468.46",
        amount_due="1468.46",
    )
    return base.model_copy(update=changes)


def document(doc_id: str, labels: ExtractedInvoice) -> manifest.Document:
    return manifest.Document(
        id=doc_id,
        source="synthetic",
        origin=doc_id,
        layout="letter",
        variant="original",
        split="test",
        media_type="application/pdf",
        file=f"{doc_id}.pdf",
        pages=1,
        sha256="0" * 64,
        labels=to_invoice_model(labels),
    )


@pytest.fixture
def eval_root(tmp_path: Path) -> Path:
    """Two documents: one read correctly, one with a misread IBAN (caught by the checksum)."""
    data = manifest.Manifest(
        name="tiny",
        generator="test",
        documents=[document("a", answer()), document("b", answer())],
    )
    (tmp_path / "dataset").mkdir()
    manifest.save(data, tmp_path / "dataset" / "manifest.json")
    header = recording.RunHeader(
        run_id="run1",
        extractor="azure",
        model="gpt-5.4-mini-2026-03-17",
        deployment="gpt-5.4-mini",
        reasoning_effort="low",
        prompt_fingerprint=gate.current_fingerprint(),
        dataset_version=manifest.version(tmp_path / "dataset" / "manifest.json"),
        split="test",
        started=datetime(2026, 11, 25, 9, 0, tzinfo=UTC),
        today=date(2026, 11, 25),
    )
    text = "Rechnung RE-2026-0042 USt-IdNr. DE123456789 IBAN DE02 1001 0010 0006 8201 01 1.468,46"
    recordings = [
        recording.Recording(
            doc_id="a",
            answer=answer().model_dump(),
            text=text,
            input_tokens=2000,
            output_tokens=500,
            seconds=3.0,
        ),
        recording.Recording(
            doc_id="b",
            answer=answer(iban="DE02 1001 0010 0006 8201 02").model_dump(),
            text=text,
            input_tokens=2000,
            output_tokens=500,
            seconds=5.0,
        ),
    ]
    recording.write(tmp_path / "recordings" / "run1", header, recordings)
    baseline = gate.make_baseline(tmp_path, "run1")
    (tmp_path / "baseline.json").write_text(baseline.model_dump_json(), encoding="utf-8")
    return tmp_path
