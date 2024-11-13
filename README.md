This repository contains an experimental utility to monitor the visual output of
cells from Jupyter notebooks.

## Installing

To install, check out this repository and:

    pip install -e .

Python 3.10 or later is supported (Python 3.12 or later on Windows).

If this is the first time using playwright, you will also need to run:

    playwright install firefox

## Quick start

First, write one or more blocks of code you want to benchmark each in a cell. In
addition, as early as possible in the notebook, make sure you set the border
color on any ipywidget layout you want to record:

    widget.layout.border = '1px solid rgb(143, 56, 3)'

The R and G values should be kept as (143, 56), and the B color should be unique for each widget and be a value between 0 and 255 (inclusive).

Then, to run the notebook and monitor the changes in widget output, run:

    jupyter-output-monitor monitor --notebook mynotebook.ipynb

Where ``mynotebook.ipynb`` is the name of your notebook. By default, this will
open a window showing you what is happening, but you can also pass ``--headless``
to run in headless mode.

## Using this on a remote Jupyter Lab instance

If you want to test this on an existing Jupyter Lab instance, including
remote ones, you can use ``--url`` instead of ``--notebook``:

    jupyter-output-monitor monitor --url http://localhost:8987/lab/tree/notebook.ipynb?token=7bb9a...

Note that the URL should include the path to the notebook, and will likely
require the token too.

You should make sure that all output cells in the notebook have been cleared
before running the above command, and that the widget border color has been
set as mention in the **Quick start** guide above.

If you make use of the [jupyter-collaboration](https://github.com/jupyterlab/jupyter-collaboration) plugin on the Jupyter Lab server, you will be able to
more easily e.g. clear the output between runs and edit the notebook in
between runs of ``jupyter-output-monitor``.

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

## Generating a report

You can generate a copy of the input notebook with output screenshots and profiling
results inserted by using e.g.:

    jupyter-output-monitor report --notebook mynotebook.ipynb --results-dir=output

Where ``--results-dir`` is the output directory generated with the ``monitor``
command. BY default, this will write a ``report.ipynb`` notebook, but you can
overwrite the filename with ``--output-report-name``.
