import json
from decimal import Decimal
from pathlib import Path

import pytest
from belegfluss.extraction import schema

from belegfluss_eval import gate


def test_gate_passes_on_the_baseline(eval_root: Path) -> None:
    assert gate.check(eval_root) == []


def test_baseline_numbers(eval_root: Path) -> None:
    summary = gate.Baseline.model_validate_json((eval_root / "baseline.json").read_bytes()).summary
    assert summary["documents"] == 2
    assert summary["document_accuracy"] == 0.5  # document b has a misread IBAN
    assert summary["field_accuracy"]["iban"] == 0.5
    assert summary["catch_rate"] == 1.0  # the IBAN checksum flags it
    assert summary["false_alarm_rate"] == 0.0


def test_a_parsing_bug_is_blocked(eval_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = schema.parse_amount

    def broken(text: str | None) -> Decimal | None:  # forgets German thousands separators
        if text and "." in text and "," not in text:
            text = text.split(".")[0]
        return original(text)

    monkeypatch.setattr(schema, "parse_amount", broken)
    problems = gate.check(eval_root)
    assert any(p.startswith("gross:") for p in problems)
    assert any(p.startswith("document_accuracy:") for p in problems)


def test_a_prompt_change_needs_a_new_live_run(
    eval_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gate, "current_fingerprint", lambda: "something else")
    assert gate.check(eval_root) == [
        "prompt, schema or model settings changed: run a live evaluation and update the baseline"
    ]


def test_a_changed_dataset_needs_a_new_live_run(eval_root: Path) -> None:
    path = eval_root / "dataset" / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["documents"][0]["labels"]["number"] = "RE-2026-0099"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert gate.check(eval_root) == [
        "dataset changed: run a live evaluation and update the baseline"
    ]


def test_an_ablation_cannot_become_the_baseline(eval_root: Path) -> None:
    header_path = eval_root / "recordings" / "run1" / "header.json"
    header = json.loads(header_path.read_text(encoding="utf-8"))
    header["options"] = {"input": "image-only"}
    header_path.write_text(json.dumps(header), encoding="utf-8")
    with pytest.raises(ValueError, match="standard Azure run"):
        gate.make_baseline(eval_root, "run1")
