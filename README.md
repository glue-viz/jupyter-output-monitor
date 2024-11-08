This repository contains an experimental utility to monitor the visual output of
cells from Jupyter notebooks.

## Requirements

On the machine being used to run the ``monitor_cells.py``:

* [numpy](https://numpy.org)
* [click](https://click.palletsprojects.com/en/stable/)
* [pillow](https://python-pillow.org/)
* [playwright](https://pypi.org/project/playwright/)
* [nbformat](https://pypi.org/project/nbformat/)

On the Jupyter Lab server, optionally (but recommended):

* [jupyter-collaboration](https://github.com/jupyterlab/jupyter-collaboration)

If this is the first time using playwright, you will need to run::

    playwright install firefox

## Installing

To install, check out this repository and:

    pip install -e .

## How this works

The general approach here is to use playwright to open a notebook, and run the
cells one by one, and the script will then watch for any output cells that have
a special border and take screenshots of them and any changes.

This border is identified by having a very specific set of 256 colors which is
``(143, 56, *)``. If a cell output contains a frame with a border that has this
color, then we start recording screenshots for this cells, where the blue color
gives the index of the set of screenshots. For instance, if ``*`` is 3, the
script will save a set of screenshots that looks like:

    output-003-2024-11-06T11:13:05.657891.png
    output-003-2024-11-06T11:13:06.468521.png
    output-003-2024-11-06T11:13:06.733932.png
    output-003-2024-11-06T11:13:06.982627.png
    output-003-2024-11-06T11:13:07.238872.png
    output-003-2024-11-06T11:13:08.075732.png

Screenshots are only saved if the output has changed. By default, the bytes of the
screenshot have to match the previous one exactly in order to not be saved, though
we could make it have some amount of tolerance.

In addition to screenshots, an event log ``event_log.csv`` is written out in csv
format, and looks like:

    time,event,index,screenshot
    2024-11-06T23:47:10.156918,execute-input,0,output-2024-11-06T23:46:59.265044/input-000-2024-11-06T23:47:10.156918.png
    2024-11-06T23:47:10.938298,output-changed,201,output-2024-11-06T23:46:59.265044/output-201-2024-11-06T23:47:10.938298.png
    2024-11-06T23:47:11.456103,output-changed,201,output-2024-11-06T23:46:59.265044/output-201-2024-11-06T23:47:11.456103.png
    2024-11-06T23:47:20.848153,execute-input,1,output-2024-11-06T23:46:59.265044/input-001-2024-11-06T23:47:20.848153.png
    2024-11-06T23:47:22.643143,output-changed,201,output-2024-11-06T23:46:59.265044/output-201-2024-11-06T23:47:22.643143.png
    2024-11-06T23:47:31.346982,execute-input,2,output-2024-11-06T23:46:59.265044/input-002-2024-11-06T23:47:31.346982.png
    2024-11-06T23:47:41.713318,execute-input,3,output-2024-11-06T23:46:59.265044/input-003-2024-11-06T23:47:41.713318.png
    2024-11-06T23:47:42.525010,output-changed,201,output-2024-11-06T23:46:59.265044/output-201-2024-11-06T23:47:42.525010.png
    2024-11-06T23:47:42.973950,output-changed,201,output-2024-11-06T23:46:59.265044/output-201-2024-11-06T23:47:42.973950.png

This shows when each input was executed, as well as any associated screenshot.
The ``index`` column gives the index of the input cell in the notebook for the
``execute-input`` events, though note that this may not always line up with
Jupyter's numbering, so to avoid any confusion, a matching screenshot of the
input cell is taken. For ``output-changed`` events, the index is that given by
the border color as described above.

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

## Headless vs non-headless mode

By default, the script will open up a window and show what it is doing. It will
also wait until it detects any input cells before proceeding. This then gives
you the opportunity to enter any required passwords, and open the correct
notebook. However, note that if Jupyter Lab opens up with a different notebook
to the one you want by default, it will start executing that one! It's also
better if the notebook starts off with output cells cleared, otherwise the script
may start taking screenshots straight away.

The easiest way to ensure that the correct notebook gets executed and that it
has had its output cells cleared is to make use of the
[jupyter-collaboration](https://github.com/jupyterlab/jupyter-collaboration)
plugin. With this plugin installed, you can open Jupyter Lab in a regular browser window,
and set it up so that the correct notebook is open by default and has its cells cleared,
and you can then launch the monitoring script. In fact, if you do this you can then
also run the script in headless mode since you know it should be doing the right thing.

One final note is that to avoid any jumping up and down of the notebook during
execution, the window opened by the script has a very large height so that the
full notebook fits inside the window without scrolling.

## How to use

* Assuming you have installed
  [jupyter-collaboration](https://github.com/jupyterlab/jupyter-collaboration),
  start up Jupyter Lab instance on a regular browser and go to the notebook you
  want to profile.
* If not already done, write one or more blocks of code you want to benchmark
  each in a cell. In addition, as early as possible in the notebook, make sure
  you set the border color on any ipywidget layout you want to record.
* Make sure the notebook you want to profile is the main one opened and that
  you have cleared any output cells.
* Run the main command in this package, specifying the URL to connect to for Jupyter Lab, e.g.:

      jupyter-output-monitor http://localhost:8987

## Settings


### Headless

To run in headless mode, include ``--headless``

### Time between cell executions

Since the monitoring script has no way of knowing when a cell has finished fully
executing, including any UI updates which might happen after the Python code has
finished running, we use a simpler approach - we execute each cell a fixed time
after the previous one. This is 10s by default but can be customized with
``--wait-after-execute=20`` for example. You should set this value so that the
cell that takes the longest to fully execute will be expected to take less than
this time.

### Notebook copy

To save a copy of the notebook with the profiling results and
screenshots inserted after the executed code cells,
include ``--notebook-copy /path/to/notebook.ipynb``.
