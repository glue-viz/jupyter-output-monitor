# # This script will use open a URL to a Jupyter Lab instance with Playwright and
# will watch for output cells that have a border that has a special color, and
# will then record any changes in that output until the script is terminated.

import os
import sys
import click
import datetime

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from io import BytesIO


RG_SPECIAL = (143, 56)


def calculate_std(bytes1, bytes2):
    array1 = np.array(Image.open(BytesIO(bytes1)))
    array2 = np.array(Image.open(BytesIO(bytes2)))
    return np.std(array1 - array2)

def isotime():
    return datetime.datetime.now().isoformat()

@click.command()
@click.argument('url')
@click.option('--output', default=None, help='Output directory - if not specified, this defaults to output_<timestamp>')
def monitor(url, output):

    if output is None:
        output = f'output-{isotime()}'

    if os.path.exists(output):
        print('Output directory {output} already exists')
        sys.exit(1)

    os.makedirs(output)

    # Index of the current last screenshot, by output index
    last_screenshot = {}

    with sync_playwright() as p, open(os.path.join(output, 'times.csv'), 'w') as log:

        log.write('index,time,std\n')
        log.flush()

        # Launch browser and open URL

        browser = p.firefox.launch(headless=False)
        page = browser.new_page(viewport={'width':2000, 'height':1500})
        page.goto(url)

        # At this point, we just start monitoring for output cells. The user
        # may need to e.g. log in to Jupyter, open the notebook, etc. The code
        # below won't do anything until there are cells in the window that have
        # a border with the special color.

        while True:

            try:
                output_cells = list(page.query_selector_all('.jp-OutputArea-output'))
            except:
                continue

            for output_cell in output_cells:

                # The element we are interested in is one level down
                div = output_cell.query_selector('div')

                if div is None:
                    continue

                style = div.get_attribute('style')

                if style is None or 'border-color: rgb(' not in style:
                    continue

                # Parse rgb values for border
                start = style.index('border-color:')
                start = style.index('(', start) + 1
                end = style.index(')', start)
                r, g, b = [int(x) for x in style[start:end].split(',')]

                # The (r,g) value pair is chosen to be random and unlikely to
                # happen by chance on the page. If this values don't match, we
                # might be looking at another element that has a border by
                # chance
                if (r, g) != RG_SPECIAL:
                    continue

                # The b value gives the index of the cell being monitored, so
                # we can currently monitor up to 255 different output cells,
                # which should be sufficient
                output_index = b

                # We now take a screenshot of the cell
                screenshot_bytes = div.screenshot()
                # screenshot_bytes = page.screenshot()

                # If screenshot didn't exist before for this cell or if it has
                # changed, we save it to a file and keep track of it.
                if output_index not in last_screenshot or last_screenshot[output_index] != screenshot_bytes:
                    time = isotime()
                    image = Image.open(BytesIO(screenshot_bytes))
                    image.save(os.path.join(output, f'{output_index:03d}-{time}.png'))
                    if output_index in last_screenshot:
                        std = calculate_std(screenshot_bytes, last_screenshot[output_index])
                    else:
                        std = 0.
                    log.write(f'{output_index},{time},{std}\n')
                    log.flush()
                    print(f"Saving screenshot of output {output_index} at {time} (std={std})")
                    last_screenshot[output_index] = screenshot_bytes

            page.wait_for_timeout(100)


if __name__ == '__main__':
    monitor()
