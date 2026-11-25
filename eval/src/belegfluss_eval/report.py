"""Reports in Markdown (for people) and JSON (for comparisons), committed to eval/reports/."""

import json
from dataclasses import asdict
from pathlib import Path

from belegfluss_eval import manifest, recording
from belegfluss_eval.metrics import FIELDS, Scored, Summary, by_group, summarise
from belegfluss_eval.paths import MANIFEST, RECORDINGS, REPORTS
from belegfluss_eval.scoring import reader_for, score


def scored_run(run: str) -> tuple[recording.RunHeader, list[Scored]]:
    data = manifest.load(MANIFEST)
    documents = {d.id: d for d in data.documents}
    header, recordings = recording.read(RECORDINGS / run)
    reader = reader_for(header)
    return header, [score(documents[r.doc_id], r, header, reader) for r in recordings]


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f} %"


def _headline(summary: Summary) -> list[str]:
    low, high = summary.document_interval
    accuracy = _percent(summary.document_accuracy)
    seconds = f"{summary.seconds_p50:.1f} / {summary.seconds_p95:.1f}"
    return [
        f"| Documents | {summary.documents} |",
        f"| **Document accuracy** (all export fields right) | **{accuracy}**"
        f" (95 % CI {_percent(low)} to {_percent(high)}) |",
        f"| Catch rate (wrong documents flagged) | {_percent(summary.catch_rate)} |",
        f"| False alarms (correct documents flagged) | {_percent(summary.false_alarm_rate)} |",
        f"| Cost per document | ${summary.cost_per_document_usd:.4f} |",
        f"| Seconds per document, p50 / p95 | {seconds} |",
    ]


def write(runs: list[str], name: str) -> Path:
    """One report for one or more runs (the first is the main one, the others are compared)."""
    results = [scored_run(run) for run in runs]
    header, main = results[0]
    lines = [
        f"# Evaluation report: {name}",
        "",
        f"- Runs: {', '.join(f'`{r}`' for r in runs)}",
        f"- Extractor: {header.extractor}, model `{header.model}`, "
        f"deployment `{header.deployment}`, reasoning effort `{header.reasoning_effort}`",
        f"- Prompt fingerprint: `{(header.prompt_fingerprint or '-')[:12]}`; "
        f"dataset version `{header.dataset_version[:12]}`; split `{header.split}`; "
        f"date {header.today}",
        "- Scored with the production mapping and checks (`eval/src/belegfluss_eval/scoring.py`).",
        "",
        "## Headline",
        "",
        "| | |",
        "|---|---|",
        *_headline(summarise(main)),
        "",
        "## Accuracy per field",
        "",
        "| Field | " + " | ".join(f"`{r}`" for r in runs) + " |",
        "|---|" + "---:|" * len(runs),
    ]
    summaries = [summarise(scored) for _, scored in results]
    for field_name in FIELDS:
        cells = " | ".join(_percent(s.field_accuracy[field_name]) for s in summaries)
        lines.append(f"| {field_name} | {cells} |")
    lines.append(
        "| **document** | "
        + " | ".join(f"**{_percent(s.document_accuracy)}**" for s in summaries)
        + " |"
    )
    lines.append(
        "| cost / document | "
        + " | ".join(f"${s.cost_per_document_usd:.4f}" for s in summaries)
        + " |"
    )
    lines.append("| seconds p50 | " + " | ".join(f"{s.seconds_p50:.1f}" for s in summaries) + " |")

    lines += ["", "## By source and variant (main run)", ""]
    lines += ["| Group | Documents | Document accuracy | 95 % CI | Catch rate | False alarms |"]
    lines += ["|---|---:|---:|---|---:|---:|"]
    for group, summary in by_group(main).items():
        low, high = summary.document_interval
        lines.append(
            f"| {group} | {summary.documents} | {_percent(summary.document_accuracy)} | "
            f"{_percent(low)} to {_percent(high)} | {_percent(summary.catch_rate)} | "
            f"{_percent(summary.false_alarm_rate)} |"
        )
    short = [s for s in main if s.pages <= 2]
    if len(short) != len(main):
        s = summarise(short)
        lines += [
            "",
            "Documents with at most 2 pages (what Document Intelligence F0 can read): "
            f"{s.documents}, "
            f"document accuracy {_percent(s.document_accuracy)}.",
        ]

    examples = [(s.doc_id, f, e, g) for s in main for f, (e, g) in s.differences.items()]
    lines += ["", f"## Wrong fields (main run, first 25 of {len(examples)})", ""]
    lines += ["| Document | Field | Expected | Read |", "|---|---|---|---|"]
    for doc_id, field_name, expected, got in examples[:25]:
        lines.append(f"| {doc_id} | {field_name} | {expected} | {got} |")

    REPORTS.mkdir(parents=True, exist_ok=True)
    target = REPORTS / f"{name}.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    data = {run: asdict(s) for run, s in zip(runs, summaries, strict=True)}
    (REPORTS / f"{name}.json").write_text(
        json.dumps(data, indent=1, default=str) + "\n", encoding="utf-8", newline="\n"
    )
    return target
