import csv
import subprocess
import sys
from pathlib import Path

DATA = Path(__file__).parent / "data"


def test_simple(tmp_path):
    output_path = tmp_path / "output"
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
        ],
        check=True,
    )

    # Check that the expected screenshots are there

    # Input cells
    assert len(list(output_path.glob("input-*.png"))) == 5

    # Output screenshots
    assert len(list(output_path.glob("output-*.png"))) == 4

    # Specifically for cell with index 33
    assert len(list(output_path.glob("output-003-*.png"))) == 1

    # Specifically for cell with index 33
    assert len(list(output_path.glob("output-033-*.png"))) == 3

    # Check that event log exists and is parsable
    with open(output_path / "event_log.csv") as f:
        reader = csv.reader(f, delimiter=",")
        assert len(list(reader)) == 10

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
