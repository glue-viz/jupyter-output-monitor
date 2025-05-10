import csv
import subprocess
import sys
from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data"


@pytest.mark.parametrize("threshold", [None, 2])
def test_simple(output_path, threshold):
    if threshold:
        output_path = output_path / "simple_threshold"
    else:
        output_path = output_path / "simple"
    extra = [] if threshold is None else ["--atol", str(threshold)]
    subprocess.run(
        [
            sys.executable,
            "-m",
            "jupyter_output_monitor",
            "monitor",
            "--notebook",
            str(DATA / "simple.ipynb"),
            "--output",
            str(output_path),
            "--headless",
            *extra,
        ],
        check=True,
    )

    # Check that the expected screenshots are there

    # Input cells
    assert len(list(output_path.glob("input-*.png"))) == 5

    # Output screenshots
    if threshold:
        assert len(list(output_path.glob("output-*.png"))) in (4, 5)
    else:
        assert len(list(output_path.glob("output-*.png"))) >= 4

    # Specifically for cell with index 3
    if threshold:
        assert len(list(output_path.glob("output-003-*.png"))) == 1
    else:
        assert len(list(output_path.glob("output-003-*.png"))) >= 1

    # Specifically for cell with index 33
    if threshold:
        assert len(list(output_path.glob("output-033-*.png"))) in (3, 4)
    else:
        assert len(list(output_path.glob("output-033-*.png"))) >= 3

    # Check that event log exists and is parsable
    with open(output_path / "event_log.csv") as f:
        reader = csv.reader(f, delimiter=",")
        if threshold:
            assert len(list(reader)) in (10, 11)
        else:
            assert len(list(reader)) >= 10

    subprocess.run(
        [
            sys.executable,
            "-m",
            "jupyter_output_monitor",
            "report",
            "--notebook",
            str(DATA / "simple.ipynb"),
            "--results-dir",
            str(output_path),
        ],
        check=True,
    )

    assert (output_path / "report.ipynb").exists()
