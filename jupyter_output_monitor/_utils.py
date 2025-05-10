import datetime
import io
import socket

import numpy as np
from nbconvert import NotebookExporter
from PIL import Image
from traitlets.config import Config

__all__ = ["get_free_port", "clear_notebook", "isotime", "max_uint8_difference"]


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


def max_uint8_difference(image1_bytes, image2_bytes):
    # Load images from bytes
    image1 = Image.open(io.BytesIO(image1_bytes)).convert("RGB")
    image2 = Image.open(io.BytesIO(image2_bytes)).convert("RGB")

    # Convert images to numpy arrays
    array1 = np.array(image1, dtype=np.uint8)
    array2 = np.array(image2, dtype=np.uint8)

    # Ensure both images have the same dimensions
    if array1.shape != array2.shape:
        return 256

    # Calculate the absolute difference
    diff = np.abs(array1.astype(np.int16) - array2.astype(np.int16))

    # Find the maximum difference
    max_diff = np.max(diff)

    return max_diff
