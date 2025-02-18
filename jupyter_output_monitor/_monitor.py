# This script will use open a URL to a Jupyter Lab instance with Playwright and
# will watch for output cells that have a border that has a special color, and
# will then record any changes in that output until the script is terminated.

import os
import sys
import tempfile
import time
from io import BytesIO

import click
from PIL import Image
from playwright.sync_api import sync_playwright

from ._server import jupyter_server
from ._utils import clear_notebook, isotime

__all__ = ["monitor", "monitor_group"]

RG_SPECIAL = (143, 56)


def iso_to_path(time):
    return time.replace(":", "-")


@click.group()
def monitor_group():
    pass


@monitor_group.command()
@click.option(
    "--notebook",
    default=None,
    help="The notebook to profile. If specified a local Jupyter Lab instance will be run",
)
@click.option(
    "--url",
    default=None,
    help="The URL hosting the notebook to profile, including any token and notebook path.",
)
@click.option(
    "--output",
    default=None,
    help="Output directory - if not specified, this defaults to output_<timestamp>",
)
@click.option(
    "--wait-after-execute",
    default=10,
    help="Time in s to wait after executing each cell",
)
@click.option("--headless", is_flag=True, help="Whether to run in headless mode")
def monitor(notebook, url, output, wait_after_execute, headless):
    if output is None:
        output = f"output-{iso_to_path(isotime())}"

    if os.path.exists(output):
        print(f"Output directory {output} already exists")
        sys.exit(1)

    os.makedirs(output)

    if notebook is None and url is None:
        print("Either --notebook or --url should be specified")
        sys.exit(1)
    elif notebook is not None and url is not None:
        print("Only one of --notebook or --url should be specified")
        sys.exit(1)
    elif notebook is not None:
        # Create a temporary directory with a clean version of the notebook
        notebook_dir = tempfile.mkdtemp()
        clear_notebook(notebook, os.path.join(notebook_dir, "notebook.ipynb"))
        with jupyter_server(notebook_dir) as server:
            url = server.base_url + "/lab/tree/notebook.ipynb"
            _monitor_output(url, output, wait_after_execute, headless)
    else:
        _monitor_output(url, output, wait_after_execute, headless)


def _monitor_output(url, output, wait_after_execute, headless):
    # Index of the current last screenshot, by output index
    last_screenshot = {}

    with (
        sync_playwright() as p,
        open(os.path.join(output, "event_log.csv"), "w") as log,
    ):
        log.write("time,event,index,screenshot\n")
        log.flush()

        # Launch browser and open URL

        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 2000, "height": 10000})
        page.goto(url)

        while True:
            print("Checking for input cells")

            # Construct list of input and output cells in the notebook
            input_cells = list(page.query_selector_all(".jp-InputArea-editor"))

            # Keep only input cells that are visible
            input_cells = [cell for cell in input_cells if cell.is_visible()]

            if len(input_cells) > 0:
                break

            print("-> No input cells found, waiting before checking again")

            # If no visible input cells, wait and try again
            page.wait_for_timeout(1000)

        print(f"{len(input_cells)} input cells found")

        # Take screenshot of the whole page, for the record
        screenshot_bytes = page.screenshot()

        timestamp = isotime()

        screenshot_filename = os.path.join(
            output,
            f"page-{iso_to_path(timestamp)}.png",
        )
        image = Image.open(BytesIO(screenshot_bytes))
        image.save(screenshot_filename)

        # Check if server is asking us to select a kernel
        dialogs = list(page.query_selector_all(".jp-Dialog-header"))
        for dialog in dialogs:
            if 'Select Kernel' in dialog.inner_text():
                print("Server is asking to select a kernel, accepting default")
                accept = list(page.query_selector_all(".jp-mod-accept"))
                if len(accept) == 1:
                    accept[0].click()
                else:
                    print("Error: multiple accept buttons found, not sure which to click")
                    sys.exit(1)

        last_screenshot = {}

        # Now loop over each input cell and execute
        for input_index, input_cell in enumerate(input_cells):
            if input_cell.text_content().strip() == "":
                print(f"Skipping empty input cell {input_index}")
                continue

            print(f"Execute input cell {input_index}")

            # Take screenshot before we start executing cell but save it after
            screenshot_bytes = input_cell.screenshot()

            # Select cell
            input_cell.click()

            # Execute it
            page.keyboard.press("Shift+Enter")

            timestamp = isotime()

            screenshot_filename = os.path.join(
                output,
                f"input-{input_index:03d}-{iso_to_path(timestamp)}.png",
            )
            image = Image.open(BytesIO(screenshot_bytes))
            image.save(screenshot_filename)

            log.write(
                f"{timestamp},execute-input,{input_index},{screenshot_filename}\n",
            )

            # Now loop and check for changes in any of the output cells - if a cell
            # output changes, save a screenshot

            print("Watching for changes in output cells")

            start = time.time()
            while time.time() - start < wait_after_execute:
                output_cells = list(page.query_selector_all(".jp-OutputArea-output"))

                for output_cell in output_cells:
                    if not output_cell.is_visible():
                        continue

                    # The element we are interested in is one level down

                    for child in output_cell.query_selector_all("*"):
                        style = child.get_attribute("style")
                        if style is not None and "border-color: rgb(" in style:
                            break
                    else:
                        continue

                    # Parse rgb values for border
                    start_pos = style.index("border-color:")
                    start_pos = style.index("(", start_pos) + 1
                    end_pos = style.index(")", start_pos)
                    r, g, b = (int(x) for x in style[start_pos:end_pos].split(","))

                    # The (r,g) pair is chosen to be random and unlikely to
                    # happen by chance on the page. If this values don't match, we
                    # might be looking at another element that has a border by
                    # chance
                    if (r, g) != RG_SPECIAL:
                        continue

                    # The b value gives the index of the cell being monitored, so
                    # we can currently monitor up to 255 different output cells,
                    # which should be sufficient
                    output_index = b

                    print(f"- taking screenshot of output cell {output_index}")

                    screenshot_bytes = child.screenshot()

                    # If screenshot didn't exist before for this cell or if it has
                    # changed, we save it to a file and keep track of it.
                    if (
                        output_index not in last_screenshot
                        or last_screenshot[output_index] != screenshot_bytes
                    ):
                        print(" -> change detected!")

                        timestamp = isotime()

                        screenshot_filename = os.path.join(
                            output,
                            f"output-{output_index:03d}-{iso_to_path(timestamp)}.png",
                        )
                        image = Image.open(BytesIO(screenshot_bytes))
                        image.save(screenshot_filename)

                        log.write(
                            f"{timestamp},output-changed,{output_index},{screenshot_filename}\n",
                        )
                        log.flush()

                        print(
                            f"Saving screenshot of output {output_index} at {timestamp}",
                        )

                        last_screenshot[output_index] = screenshot_bytes

            print("Stopping monitoring output and moving on to next input cell")


if __name__ == "__main__":
    monitor()
