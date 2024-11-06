This repository contains an experimental utility to monitor the visual output of
cells from Jupyter notebooks.

## Requirements

On the machine being used to run the ``monitor_cells.py``:

* [numpy](https://numpy.org)
* [click](https://click.palletsprojects.com/en/stable/)
* [pillow](https://python-pillow.org/)
* [playwright](https://pypi.org/project/playwright/)

On the Jupyter Lab server:

* [jupyter-collaboration](https://github.com/jupyterlab/jupyter-collaboration)

If this is the first time using playwright, you will need to run::

    playwright install firefox

## Approach and Motivation

The general approach here is to use playwright to open a notebook, and the script
will then watch for any cells that have a special border. This border is identified
by having a very specific set of 256 colors which is ``(143, 56, *)``. If a cell
output contains a frame with a border that has this color, then we start recording
screenshots for this cells, where the blue color gives the index of the set of
screenshots. For instance, if ``*`` is 3, the script will save a set of screenshots
that looks like:

    003-2024-11-06T11:13:05.657891.png
    003-2024-11-06T11:13:06.468521.png
    003-2024-11-06T11:13:06.733932.png
    003-2024-11-06T11:13:06.982627.png
    003-2024-11-06T11:13:07.238872.png
    003-2024-11-06T11:13:08.075732.png
    003-2024-11-06T11:13:08.347225.png
    003-2024-11-06T11:13:08.591041.png

Screenshots are only saved if the output has changed. By default, the bytes of the
screenshot have to match the previous one exactly in order to not be saved, though
we could make it have some amount of tolerance.

On the monitoring side, this is all that happens - screenshots are saved for cells
with a special frame color, for any change in the output.

We now look at how to set the frame color and trigger the recording. In order to
start recording a cell output, the top level of that cell output has to be an
ipywidget object. The ``.layout`` on that object can then be set to add a border
color. For example, if using glue-jupyter, one can do:

    scatter = app.scatter2d()
    scatter.layout.layout.border = '2px solid rgb(143, 56, 3)'

and if using jdaviz:

    imviz.app.layout.border = '2px solid rgb(143, 56, 3)'

To stop recording output for a given cell, you can set the border attribute to
``''``.

In theory, it is possible to add borders to multiple output cells in the
notebook, but this will cause severe flickering as playwright needs to scroll to
each different output in order to take screenshots. Furthermore, even when
taking screenshots of a single cell, this makes it difficult to type any input
into the notebook due to the jumping up and down of the notebook. Therefore,
assuming we are not doing headless tests for now, the easiest approach is
actually to use the jupyter-collaboration plugin, and to have a main browser
window open (not with playwright) from which you control the notebook, and then
connect to the same Jupyter instance using playwright and not to interfere with
any scrolling or input in that browser.

In this case it is still best not to have multiple cells that have a border at
any one time as this will still cause jumping around and the screenshots do not
always work properly in this case.

Instead, the best approach is likely to have a single cell where the output is
being measured, but one can still have several benchmarks that change the blue
component of the border color over time to indicate the index of the benchmark
being carried out.

## Instructions

* Assuming you have installed
  [jupyter-collaboration](https://github.com/jupyterlab/jupyter-collaboration),
  start up Jupyter Lab instance on a regular browser and go to the notebook you
  want to profile.
* Write a block of code you want to benchmark in a cell, and at the start of
  that cell, set the border color for the output cell you want to take
  screenshots of. Don't reset the color of the border at the end of the cell
  otherwise the screenshots will prematurely stop once the Python code in the
  cell has stopped executing rather than when the UI has finished updating. Once
  you are happy with the benchmark you have set up, make sure you clear any
  output cells before continuing (otherwise screenshots will start being taken
  straight away in the next step).
* Run the script in this repository, specifying the URL to connect to for Jupyter Lab, e.g.:

        python monitor_cells.py http://localhost:8987

  and navigate to the notebook you want, optionally entering any password etc.
* In the main browser, execute the cell(s) needed to make the benchmark run. The
  border color should immediately change and immediately trigger a screenshot,
  regardless of whether the rest of the UI has had any updates yet

## Results

In addition to screenshots being saved to the output directory, there is a
``times.csv`` file that lists the output cell index (based on the B part of the
RGB color, not the Jupyter cell numbering), the ISO time, and the standard
deviation of the current screenshot in RGB space compared to the last version.

## Wish list (and why some of these aren't trivial)

* A utility or context manager to automatically set the border color
  automatically and then remove it at the end of a block of code. This isn't
  trivial because in fact we don't want to reset the border color once the
  Python block has executed, since the UI may continue to update after this.
* Allow some tolerance between screenshots to not output too many for any changed byte
* Output a csv file with machine-readable times for each screenshot
