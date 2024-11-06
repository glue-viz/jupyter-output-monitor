# This script will use open a URL to a Jupyter Lab instance with Playwright and
# will watch for output cells that have a border that has a special color, and
# will then record any changes in that output until the script is terminated.

import os
import sys
import time
import click
import datetime

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from io import BytesIO


RG_SPECIAL = (143, 56)

def isotime():
    return datetime.datetime.now().isoformat()

@click.command()
@click.argument('url')
@click.option('--output', default=None, help='Output directory - if not specified, this defaults to output_<timestamp>')
@click.option('--wait-after-execute', default=10, help='Time in s to wait after executing each cell')
@click.option('--headless', is_flag=True, help='Whether to run in headless mode')
def monitor(url, output, wait_after_execute, headless):

    if output is None:
        output = f'output-{isotime()}'

    if os.path.exists(output):
        print('Output directory {output} already exists')
        sys.exit(1)

    os.makedirs(output)

    # Index of the current last screenshot, by output index
    last_screenshot = {}

    with sync_playwright() as p, open(os.path.join(output, 'event_log.csv'), 'w') as log:

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

            screenshot_filename = os.path.join(output, f'input-{input_index:03d}-{timestamp}.png')
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
                        screenshot_filename = os.path.join(output, f'output-{output_index:03d}-{timestamp}.png')
                        image = Image.open(BytesIO(screenshot_bytes))
                        image.save(screenshot_filename)

                        log.write(f'{timestamp},output-changed,{output_index},{screenshot_filename}\n')
                        log.flush()

                        print(f"Saving screenshot of output {output_index} at {timestamp}")

                        last_screenshot[output_index] = screenshot_bytes

            print('Stopping monitoring output and moving on to next input cell')


if __name__ == '__main__':
    monitor()
