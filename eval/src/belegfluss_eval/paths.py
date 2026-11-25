"""Where things are. Rendered files live in git-ignored testdata/external/ (ADR-0008, ADR-0018)."""

from pathlib import Path

EVAL = Path(__file__).resolve().parents[2]  # eval/
REPO = EVAL.parent
EXTERNAL = REPO / "testdata" / "external"

MANIFEST = EVAL / "dataset" / "manifest.json"
RECORDINGS = EVAL / "recordings"
REPORTS = EVAL / "reports"
TEMPLATES = EVAL / "templates"

DATASET_NAME = "eval-dataset-v1"
DATASET_FILES = EXTERNAL / DATASET_NAME  # files referenced by the manifest, relative to this folder
SUITE = EXTERNAL / "xrechnung-testsuite-2026-08-31"
VISUALISATION = EXTERNAL / "visualization-2026-10-13"
