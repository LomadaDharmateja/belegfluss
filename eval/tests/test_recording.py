from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from belegfluss_eval import recording


def test_a_new_run_never_reuses_an_earlier_runs_folder(tmp_path: Path) -> None:
    # Regression: a second run on the same day with the same prompt got the same name as the
    # committed baseline run and would have overwritten its recordings.
    run_id = "2026-11-25-azure-test-p97843178"
    assert recording.free_run_id(tmp_path, run_id) == run_id
    (tmp_path / run_id).mkdir()
    assert recording.free_run_id(tmp_path, run_id) == f"{run_id}-2"
    (tmp_path / f"{run_id}-2").mkdir()
    assert recording.free_run_id(tmp_path, run_id) == f"{run_id}-3"


def test_writing_refuses_an_existing_run_folder(tmp_path: Path) -> None:
    header = recording.RunHeader(
        run_id="run1",
        extractor="azure",
        model="m",
        dataset_version="v",
        split="test",
        started=datetime(2026, 11, 25, tzinfo=UTC),
        today=date(2026, 11, 25),
    )
    recording.write(tmp_path / "run1", header, [])
    with pytest.raises(FileExistsError):
        recording.write(tmp_path / "run1", header, [])
