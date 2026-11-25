"""The CI gate (ADR-0018): no extraction change may make the baseline numbers worse.

1. The dataset and the prompt must be the ones the baseline was recorded with. A change to either
   needs a new live run and a new baseline, which is then a visible diff in the pull request.
2. The baseline's recorded answers are scored again with the current code. Every field accuracy, the
   document accuracy and the catch rate must be at least the committed numbers. The replay is
   deterministic, so the comparison is exact.
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any

from belegfluss.extraction.azure_openai import prompt_fingerprint
from belegfluss.settings import Settings
from pydantic import BaseModel

from belegfluss_eval import manifest, recording
from belegfluss_eval.metrics import FIELDS, Summary, summarise
from belegfluss_eval.scoring import reader_for, score

TOLERANCE = 1e-9


class Baseline(BaseModel):
    run: str  # folder name in recordings/
    dataset_version: str
    prompt_fingerprint: str
    summary: dict[str, Any]


def current_fingerprint() -> str:
    """The fingerprint of what the worker would send today (code defaults, not the environment)."""
    fields = Settings.model_fields
    return prompt_fingerprint(
        str(fields["openai_deployment"].default),
        str(fields["ai_reasoning_effort"].default),
        int(fields["ai_max_pages"].default),
    )


def replay(root: Path, run: str) -> Summary:
    data = manifest.load(root / "dataset" / "manifest.json")
    documents = {d.id: d for d in data.documents}
    header, recordings = recording.read(root / "recordings" / run)
    reader = reader_for(header)
    return summarise(score(documents[r.doc_id], r, header, reader) for r in recordings)


def make_baseline(root: Path, run: str) -> Baseline:
    header, _ = recording.read(root / "recordings" / run)
    if header.extractor != "azure" or header.options or not header.prompt_fingerprint:
        raise ValueError("a baseline must be a standard Azure run (no ablation options)")
    return Baseline(
        run=run,
        dataset_version=header.dataset_version,
        prompt_fingerprint=header.prompt_fingerprint,
        summary=asdict(replay(root, run)),
    )


def check(root: Path) -> list[str]:
    """Problems found; an empty list means the gate passes."""
    baseline = Baseline.model_validate_json((root / "baseline.json").read_bytes())
    problems = []
    dataset_version = manifest.version(root / "dataset" / "manifest.json")
    if dataset_version != baseline.dataset_version:
        problems.append("dataset changed: run a live evaluation and update the baseline")
    if current_fingerprint() != baseline.prompt_fingerprint:
        problems.append(
            "prompt, schema or model settings changed: "
            "run a live evaluation and update the baseline"
        )
    if problems:
        return problems

    now = asdict(replay(root, baseline.run))
    before = baseline.summary
    if now["documents"] != before["documents"]:
        problems.append(
            f"documents: {now['documents']} replayed, baseline has {before['documents']}"
        )
    for name in FIELDS:
        if now["field_accuracy"][name] < before["field_accuracy"][name] - TOLERANCE:
            problems.append(
                f"{name}: {now['field_accuracy'][name]:.3f} < baseline "
                f"{before['field_accuracy'][name]:.3f}"
            )
    for key in ("document_accuracy", "catch_rate"):
        if before[key] is not None and (now[key] or 0.0) < before[key] - TOLERANCE:
            problems.append(f"{key}: {now[key] or 0.0:.3f} < baseline {before[key]:.3f}")
    return problems
