# Belegfluss evaluation

Measures how well Belegfluss reads invoices without structured data (plain PDFs, photos, scans), and blocks changes
that make it worse ([ADR-0018](../docs/decisions/0018-evaluation-dataset-metrics-and-gate.md)).

| Command (in `eval/`) | What it does | Needs |
|---|---|---|
| `uv run python -m belegfluss_eval gate` | Replays the recorded baseline answers through the current code and fails if any metric got worse or the prompt changed | nothing (runs in CI on every PR) |
| `uv run python -m belegfluss_eval fetch` | Downloads the rendered dataset (private release asset) and checks every SHA-256 | `gh` signed in |
| `uv run python -m belegfluss_eval run --split dev --extractor azure` | Live run against Azure OpenAI; writes recordings and a report | `az login`, `BELEGFLUSS_OPENAI_ENDPOINT`, dataset |
| `uv run python -m belegfluss_eval build-dataset` | Renders the labelled set from the official suite and the synthetic generator | Docker (FOP), Playwright Chromium |

Results: [`reports/`](reports/). The baseline the gate compares against: [`baseline.json`](baseline.json).
