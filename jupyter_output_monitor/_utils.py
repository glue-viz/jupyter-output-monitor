import datetime
import socket

from nbconvert import NotebookExporter
from traitlets.config import Config

__all__ = ["get_free_port", "clear_notebook", "isotime"]


def get_free_port():
    """Return a free port number."""
    sock = socket.socket()
    sock.bind(("", 0))
    return sock.getsockname()[1]


def clear_notebook(input_notebook, output_notebook):
    """Write out a copy of the notebook with output and metadata removed."""
    c = Config()
    c.NotebookExporter.preprocessors = [
        "nbconvert.preprocessors.ClearOutputPreprocessor",
        "nbconvert.preprocessors.ClearMetadataPreprocessor",
    ]

    exporter = NotebookExporter(config=c)
    body, resources = exporter.from_filename(input_notebook)

    with open(output_notebook, "w") as f:
        f.write(body)


def isotime():
    return datetime.datetime.now().isoformat()
