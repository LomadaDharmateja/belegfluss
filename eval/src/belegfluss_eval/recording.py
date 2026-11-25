"""What a live run stores, so it can be scored again later without calling any service.

A run folder holds `header.json` (how the run was made) and `recordings.jsonl` (one answer per
document). The CI gate replays these through the current code: a parsing or checking bug then shows
up as a lower score, at no cost and without Azure access.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel


class RunHeader(BaseModel):
    run_id: str
    extractor: Literal["azure", "di"]
    model: str  # model name and version as reported by the service
    deployment: str | None = None
    reasoning_effort: str | None = None
    prompt_fingerprint: str | None = None  # azure only, see extraction.azure_openai
    options: dict[str, str] = {}  # e.g. {"input": "image-only"} for an ablation
    dataset_version: str
    split: str
    started: datetime
    today: date  # the date the plausibility checks used: fixed, so replays give the same result


class Recording(BaseModel):
    doc_id: str
    answer: dict[str, Any] | None  # the service's structured answer; None if the call failed
    error: str | None = None
    text: str = ""  # the text layer that was sent (the presence check needs it)
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0


def free_run_id(base: Path, run_id: str) -> str:
    """`run_id`, or with -2, -3, ... if an earlier run (such as a committed one) has that name."""
    candidate, number = run_id, 1
    while (base / candidate).exists():
        number += 1
        candidate = f"{run_id}-{number}"
    return candidate


def write(folder: Path, header: RunHeader, recordings: list[Recording]) -> None:
    folder.mkdir(parents=True, exist_ok=False)  # never overwrite a recorded run
    (folder / "header.json").write_text(
        header.model_dump_json(indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    lines = "".join(r.model_dump_json() + "\n" for r in recordings)
    (folder / "recordings.jsonl").write_text(lines, encoding="utf-8", newline="\n")


def read(folder: Path) -> tuple[RunHeader, list[Recording]]:
    header = RunHeader.model_validate_json((folder / "header.json").read_bytes())
    lines = (folder / "recordings.jsonl").read_text(encoding="utf-8").splitlines()
    return header, [Recording.model_validate_json(line) for line in lines if line]
