from contextlib import contextmanager

from solara.test.pytest_plugin import (
    ServerJupyter,
)

from ._utils import get_free_port

__all__ = ["jupyter_server"]


@contextmanager
def jupyter_server(notebook_path):
    server = ServerJupyter(notebook_path, get_free_port(), "localhost")
    try:
        server.serve_threaded()
        server.wait_until_serving()
        yield server
    finally:
        server.stop_serving()
