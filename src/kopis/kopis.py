"""Kopis: pure-Python web development."""

__all__ = ["Kopis"]

import sys
import inspect
from pathlib import Path

from aiohttp import web


def _entry_script_dir() -> Path | None:
    """Return the directory of the running script, if determinable."""
    argv0 = sys.argv[0] if sys.argv else ""

    if argv0 and Path(argv0).is_file():
        return Path(argv0).resolve().parent

    # Fall back to the file of the __main__ module on the call stack
    # (covers cases where sys.argv[0] is not a file, e.g. ``python -c``).
    frame = inspect.currentframe()

    while frame is not None:
        if frame.f_globals.get("__name__") == "__main__":
            file = frame.f_globals.get("__file__")

            if file:
                return Path(file).resolve().parent

        frame = frame.f_back

    return None


class Kopis:
    """A web application served from a root directory.

    The root directory defaults to the directory of the running script.
    Files in the root directory are served as static assets, and the
    ``document`` is served at ``/``. The document is either an in-memory
    string assigned to ``k.document``, or the ``index.html`` file in the
    root directory.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        if root is not None:
            self.root = Path(root).resolve()
        else:
            self.root = _entry_script_dir() or Path.cwd()

        self._document: str | None = None
        self.app = web.Application()

        # Registered before the static route so that it takes precedence on ``/``.
        self.app.router.add_get("/", self._serve_document)

        self.app.router.add_static("/", self.root, follow_symlinks=True)

    @property
    def document(self) -> str:
        """The HTML document served at ``/``.

        Returns the in-memory document if one was assigned, otherwise
        the contents of ``index.html`` in the root directory.
        """
        if self._document is not None:
            return self._document

        index = self.root / "index.html"
        if not index.is_file():
            raise FileNotFoundError(index)

        return index.read_text()

    @document.setter
    def document(self, value: str) -> None:
        self._document = value

    async def _serve_document(
        self, _request: web.Request
    ) -> web.Response | web.FileResponse:
        if self._document is not None:
            return web.Response(text=self._document, content_type="text/html")

        index = self.root / "index.html"
        if index.is_file():
            return web.FileResponse(index)

        raise web.HTTPNotFound()

    def run(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        web.run_app(self.app, host=host, port=port)
