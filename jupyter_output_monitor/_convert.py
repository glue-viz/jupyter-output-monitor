# Experimental command to convert a notebook to a script that tests widget
# output with solara but without launching a Jupyter Lab instance. Not yet
# exposed via the public API.

import os
from textwrap import indent

import click
import nbformat


def remove_magics(source):
    lines = [line for line in source.splitlines() if not line.startswith("%")]
    return os.linesep.join(lines)


def remove_excludes(source):
    lines = [
        line for line in source.splitlines() if not line.strip().endswith("# EXCLUDE")
    ]
    return os.linesep.join(lines)


HEADER = """
import time
import solara
import playwright
import pytest_playwright
from IPython.display import display

def watch_screenshot(widget):
    display_start = time.time()
    last_change_time = display_start
    last_screenshot = None
    while time.time() - display_start < 5:
        screenshot_bytes = widget.screenshot()
        if screenshot_bytes != last_screenshot:
            last_screenshot = screenshot_bytes
            last_change_time = time.time()
    return last_screenshot, last_change_time - display_start

def test_main(page_session, solara_test):

"""

DISPLAY_CODE = """
object_to_capture.add_class("test-object")
display(object_to_capture)
captured_object = page_session.locator(".test-object")
captured_object.wait_for()
"""

PROFILING_CODE = """
last_screenshot, time_elapsed = watch_screenshot(captured_object)
print(f"Extra time waiting for display to update: {time_elapsed:.2f}s")
"""


@click.command()
@click.argument("input_notebook")
@click.argument("output_script")
def convert(input_notebook, output_script):
    nb = nbformat.read(input_notebook, as_version=4)

    with open(output_script, "w") as f:
        f.write(HEADER)

        captured = False

        for icell, cell in enumerate(nb["cells"]):
            if cell.cell_type == "markdown":
                f.write(indent(cell.source, "    # ") + "\n\n")
            elif cell.cell_type == "code":
                if cell.source.strip() == "":
                    continue

                lines = cell.source.splitlines()

                new_lines = []

                new_lines.append("cell_start = time.time()\n\n")

                for line in lines:
                    if line.startswith("%") or line.strip().endswith("# EXCLUDE"):
                        continue
                    elif line.endswith("# SCREENSHOT"):
                        new_lines.append("object_to_capture = " + line)
                        new_lines.extend(DISPLAY_CODE.splitlines())
                        captured = True
                    else:
                        new_lines.append(line)

                new_lines.append("cell_end = time.time()\n")
                new_lines.append(
                    f'print(f"Cell {icell:2d} Python code executed in           {{cell_end - cell_start:.2f}}s")',
                )

                if captured:
                    new_lines.extend(PROFILING_CODE.splitlines())

                source = os.linesep.join(new_lines)

                f.write(indent(source, "    ") + "\n\n")


if __name__ == "__main__":
    convert()
