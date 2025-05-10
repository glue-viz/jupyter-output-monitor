import pathlib
import tempfile

import pytest


@pytest.fixture()
def output_path(request):
    path_option = request.config.getoption("--output-path")
    if path_option:
        yield pathlib.Path(path_option)
    else:
        # Create a temporary directory if no path is specified
        temp_dir = tempfile.TemporaryDirectory()
        yield pathlib.Path(temp_dir.name)
        temp_dir.cleanup()
