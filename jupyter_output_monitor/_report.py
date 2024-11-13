import csv
import datetime
import os

import click
import nbformat

__all__ = ["report", "report_group"]


@click.group()
def report_group():
    pass


@report_group.command()
@click.option(
    "--notebook",
    default=None,
    help="The notebook that was profiled.",
)
@click.option(
    "--results-dir",
    default=None,
    help="Output results directory from the profiling",
)
@click.option(
    "--output-report-name",
    default="report.ipynb",
    help="Write a copy of the notebook containing screenshots and profiling results to a notebook with the specified name, in the results directory",
)
def report(notebook, results_dir, output_report_name):
    with open(os.path.join(results_dir, "event_log.csv")) as csvfile:
        reader = csv.DictReader(csvfile)
        log = list(reader)

    # convert ISO times to elapsed times from first executed cell:
    start_time = datetime.datetime.fromisoformat(log[0]["time"])
    for row in log:
        row["time"] = (
            datetime.datetime.fromisoformat(row["time"]) - start_time
        ).total_seconds()

    results = {}
    last_executed_cell = None

    # group timing results by execution cell
    for row in log:
        index = row["index"]
        event = row["event"]

        if index not in results and event == "execute-input":
            results[index] = {
                "execute-input": None,
                "output-changed": [],
            }

            results[index][event] = row
            last_executed_cell = index

        elif event == "output-changed":
            row["output_from_cell"] = last_executed_cell
            row["dt"] = (
                row["time"] - results[last_executed_cell]["execute-input"]["time"]
            )
            results[last_executed_cell][event].append(row)

    # compute "final" timing results per execution cell
    for result in results.values():
        has_outputs = len(result["output-changed"])
        result["total"] = result["output-changed"][-1]["dt"] if has_outputs else None
        result["n_updates"] = len(result["output-changed"]) if has_outputs else None

    # assemble annotations in markdown format for each executed code cell:
    markdown_annotations = []
    for idx, result in results.items():
        if len(result["output-changed"]):
            screenshot_path = os.path.basename(
                result["output-changed"][-1]["screenshot"],
            )
            markdown_annotations.append(
                f"![output screenshot]({screenshot_path})\n\n"
                f"#### Profiling result for cell {idx}: \n * {result['total']:.2f} seconds "
                f"elapsed\n * {result['n_updates']:d} output updates\n",
            )
        else:
            markdown_annotations.append(
                f"#### Profiling result for cell {idx}: \nNo output.\n",
            )

    # read in the source notebook:
    nb = nbformat.read(notebook, nbformat.NO_CONVERT)

    # create new list of cells, weaving together the existing
    # cells and the new markdown cells with profiling results
    # and screenshots:
    new_cells = []
    nonempty_code_cell_idx = -1
    for cell in nb["cells"]:
        new_cells.append(cell)
        if cell["cell_type"] == "code" and len(cell["source"]):
            nonempty_code_cell_idx += 1
            new_cells.append(
                nbformat.v4.new_markdown_cell(
                    markdown_annotations[nonempty_code_cell_idx],
                ),
            )

    nb["cells"] = new_cells

    output_notebook = os.path.join(results_dir, output_report_name)

    print(f"Writing notebook with profiling results to: {output_notebook}")

    new_notebook = nbformat.from_dict(nb)
    nbformat.write(new_notebook, output_notebook)
