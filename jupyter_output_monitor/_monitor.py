# This script will use open a URL to a Jupyter Lab instance with Playwright and
# will watch for output cells that have a border that has a special color, and
# will then record any changes in that output until the script is terminated.

import os
import sys
import time
import click
import datetime
import numpy as np
import nbformat
from collections import OrderedDict
from io import BytesIO
from PIL import Image
from playwright.sync_api import sync_playwright


RG_SPECIAL = (143, 56)

def isotime():
    return datetime.datetime.now().isoformat()

def iso_to_path(time):
    return time.replace(':', '-')


@click.command()
@click.argument('url')
@click.option(
    '--output',
    default=None,
    help='Output directory - if not specified, this defaults to output_<timestamp>'
)
@click.option(
    '--wait-after-execute',
    default=10,
    help='Time in s to wait after executing each cell'
)
@click.option(
    '--headless',
    is_flag=True,
    help='Whether to run in headless mode'
)
@click.option(
    '--notebook-copy',
    default=None,
    help='If given a path to the notebook, write a copy containing screenshots and profiling results'
)
def monitor(url, output, wait_after_execute, headless, copy_notebook):

    if output is None:
        output = f'output-{iso_to_path(isotime())}'

    if os.path.exists(output):
        print('Output directory {output} already exists')
        sys.exit(1)

    os.makedirs(output)

    # Index of the current last screenshot, by output index
    last_screenshot = {}
    event_log_path = os.path.join(output, 'event_log.csv')
    with sync_playwright() as p, open(event_log_path, 'w') as log:

        log.write('time,event,index,screenshot\n')
        log.flush()

        # Launch browser and open URL

        browser = p.firefox.launch(headless=headless)
        page = browser.new_page(viewport={'width':2000, 'height':10000})
        page.goto(url)

        while True:

            print('Checking for input cells')

            # Construct list of input and output cells in the notebook
            input_cells = list(page.query_selector_all('.jp-InputArea-editor'))

            # Keep only input cells that are visible
            input_cells = [cell for cell in input_cells if cell.is_visible()]

            if len(input_cells) > 0:
                break

            print('-> No input cells found, waiting before checking again')

            # If no visible input cells, wait and try again
            page.wait_for_timeout(1000)

        print(f'{len(input_cells)} input cells found')

        last_screenshot = {}

        # Now loop over each input cell and execute
        for input_index, input_cell in enumerate(input_cells):

            if input_cell.text_content().strip() == '':
                print(f'Skipping empty input cell {input_index}')
                continue

            print(f'Execute input cell {input_index}')

            # Take screenshot before we start executing cell but save it after
            screenshot_bytes = input_cell.screenshot()

            # Select cell
            input_cell.click()

            # Execute it
            page.keyboard.press('Shift+Enter')

            timestamp = isotime()

            screenshot_filename = os.path.join(output, f'input-{input_index:03d}-{iso_to_path(timestamp)}.png')
            image = Image.open(BytesIO(screenshot_bytes))
            image.save(screenshot_filename)

            log.write(f'{timestamp},execute-input,{input_index},{screenshot_filename}\n')

            # Now loop and check for changes in any of the output cells - if a cell
            # output changes, save a screenshot

            print('Watching for changes in output cells')

            start = time.time()
            while time.time() - start < wait_after_execute:

                output_cells = list(page.query_selector_all('.jp-OutputArea-output'))

                for output_cell in output_cells:

                    if not output_cell.is_visible():
                        continue

                    # The element we are interested in is one level down

                    div = output_cell.query_selector('div')

                    if div is None:
                        continue

                    style = div.get_attribute('style')

                    if style is None or 'border-color: rgb(' not in style:
                        continue

                    # Parse rgb values for border
                    start_pos = style.index('border-color:')
                    start_pos = style.index('(', start_pos) + 1
                    end_pos = style.index(')', start_pos)
                    r, g, b = [int(x) for x in style[start_pos:end_pos].split(',')]

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

                    print(f'- taking screenshot of output cell {output_index}')

                    screenshot_bytes = div.screenshot()

                    # If screenshot didn't exist before for this cell or if it has
                    # changed, we save it to a file and keep track of it.
                    if output_index not in last_screenshot or last_screenshot[output_index] != screenshot_bytes:

                        print(f' -> change detected!')

                        timestamp = isotime()
                        screenshot_filename = os.path.join(output, f'output-{output_index:03d}-{iso_to_path(timestamp)}.png')
                        image = Image.open(BytesIO(screenshot_bytes))
                        image.save(screenshot_filename)

                        log.write(f'{timestamp},output-changed,{output_index},{screenshot_filename}\n')
                        log.flush()

                        print(f"Saving screenshot of output {output_index} at {timestamp}")

                        last_screenshot[output_index] = screenshot_bytes

            print('Stopping monitoring output and moving on to next input cell')

    if copy_notebook:
        write_profiled_notebook_copy(output, event_log_path, copy_notebook)


def write_profiled_notebook_copy(output, event_log_path, copy_notebook):
    log = np.recfromcsv(event_log_path, encoding='utf-8')
    columns = open(event_log_path).read().splitlines()[0].split(',')

    # convert ISO times to elapsed times from first executed cell:
    datetimes = [datetime.datetime.fromisoformat(dt) for dt in log['time']]
    log['time'] = [(dt - datetimes[0]).total_seconds() for dt in datetimes]

    # cast ∆t's from strings to floats:
    dtype = log.dtype.descr
    dtype[0] = ('time', float)
    log = log.astype(dtype)

    def row_to_dict(row):
        return {k: v for k, v in zip(columns, row)}

    results = OrderedDict()
    last_executed_cell = None

    # group timing results by execution cell
    for i, row in enumerate(log):
        isotime, event, index, screenshot_path = row

        if index not in results and event == 'execute-input':
            results[index] = {
                'execute-input': None,
                'output-changed': [],
            }

            results[index][event] = row_to_dict(row)
            last_executed_cell = index

        elif event == 'output-changed':
            row_dict = row_to_dict(row)
            row_dict['output_from_cell'] = last_executed_cell
            row_dict['dt'] = row_dict['time'] - results[last_executed_cell]['execute-input']['time']
            results[last_executed_cell][event].append(row_dict)

    # compute "final" timing results per execution cell
    for idx, result in results.items():
        has_outputs = len(result['output-changed'])
        result['total'] = result['output-changed'][-1]['dt'] if has_outputs else None
        result['n_updates'] = len(result['output-changed']) if has_outputs else None

    # assemble annotations in markdown format for each executed code cell:
    markdown_annotations = []
    for idx, result in results.items():
        if len(result['output-changed']):
            screenshot_path = os.path.basename(
                result['output-changed'][-1]['screenshot']
            )
            markdown_annotations.append(
                f"![output screenshot]({screenshot_path})\n\n" +
                f"#### Profiling result for cell {idx}: \n * {result['total']:.2f} seconds " +
                f"elapsed\n * {result['n_updates']:d} output updates\n"
            )
        else:
            markdown_annotations.append(
                f"#### Profiling result for cell {idx}: \nNo output.\n"
            )

    # read in the source notebook:
    nb = nbformat.read(copy_notebook, nbformat.NO_CONVERT)

    # create new list of cells, weaving together the existing
    # cells and the new markdown cells with profiling results
    # and screenshots:
    new_cells = []
    nonempty_code_cell_idx = -1
    for i, cell in enumerate(nb['cells']):
        new_cells.append(cell)
        if cell['cell_type'] == 'code' and len(cell['source']):
            nonempty_code_cell_idx += 1
            new_cells.append(
                nbformat.v4.new_markdown_cell(
                    markdown_annotations[nonempty_code_cell_idx]
                )
            )

    nb['cells'] = new_cells

    notebook_copy_path = os.path.join(
        output,
        os.path.basename(copy_notebook).replace('.ipynb', '-profiling.ipynb')
    )
    print(f'Writing notebook with profiling results to: {notebook_copy_path}')
    new_notebook = nbformat.from_dict(nb)
    nbformat.write(new_notebook, notebook_copy_path)

if __name__ == '__main__':
    monitor()
