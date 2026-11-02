"""Serve a folder of test pages to the simulator from this Mac."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Keep request logs out of test output."""


@contextmanager
def serve_directory(root: Path) -> Iterator[str]:
    """Serve ``root`` on 127.0.0.1 at a free port and yield its base URL.

    Simulators share the Mac's network, so they reach this server; physical devices do not.
    """
    if not root.is_dir():
        raise FileNotFoundError(root)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(root)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
