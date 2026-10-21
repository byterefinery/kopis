"""Kopis: pure-Python web development."""

__all__ = ["Document", "Element", "Kopis"]

import sys
import inspect
from html.parser import HTMLParser
from pathlib import Path
from typing import Self

from aiohttp import web
from bs4 import BeautifulSoup, Tag
from bs4.builder import HTMLTreeBuilder


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


#: Tags that never have children or an end tag.
_empty_tags = HTMLTreeBuilder.DEFAULT_EMPTY_ELEMENT_TAGS
_VOID_TAGS = frozenset(_empty_tags) if _empty_tags is not None else frozenset()


def _line_offsets(text: str) -> list[int]:
    """Return the offset of the first character of every line in ``text``."""
    offsets = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def _insertion_offset(text: str, tag: Tag) -> int:
    """Return the offset in ``text`` where new children of ``tag`` belong.

    ``tag`` must be an element parsed from ``text``; its ``sourceline``
    and ``sourcepos`` attributes identify which element it is. The
    returned offset is just before ``tag``'s end tag, or just before the
    end tag that implicitly closes it. If the element has no end tag in
    the document, the offset is the end of the document.
    """
    target = (tag.sourceline, tag.sourcepos)
    line_offsets = _line_offsets(text)
    found: list[int | None] = [None]

    class _Scanner(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.stack: list[tuple[str, int, int]] = []

        def _offset(self) -> int:
            line, col = self.getpos()
            return line_offsets[line - 1] + col

        def handle_starttag(
            self, tag: str, attrs: list[tuple[str, str | None]]
        ) -> None:
            if tag in _VOID_TAGS:
                return
            line, col = self.getpos()
            self.stack.append((tag, line, col))

        def handle_endtag(self, tag: str) -> None:
            if found[0] is not None:
                return
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    break
            else:
                return  # Stray end tag with no matching open tag.
            if any(entry[1:] == target for entry in self.stack[i:]):
                found[0] = self._offset()
            del self.stack[i:]

    scanner = _Scanner()
    scanner.feed(text)
    scanner.close()
    return found[0] if found[0] is not None else len(text)


class Document:
    """A live view of the HTML document served at ``/``.

    The document is stored as a plain string; :mod:`beautifulsoup4` is
    used to parse it and locate elements. Look up an element by tag name
    with either subscripting or attribute access; both return an
    :class:`Element` for the first element with that name::

        k.document["head"].append('<meta name="viewport" content="...">')
        with k.document.body as el:
            el.append("<script src=...></script>")
    """

    def __init__(self, owner: Kopis) -> None:
        self._owner = owner

    def _element(self, name: str) -> Element:
        tag = self._owner._parse().find(name)
        if tag is None:
            raise KeyError(f"no <{name}> element in the document")
        return Element(self, tag)

    def __getitem__(self, name: str) -> Element:
        return self._element(name)

    def __getattr__(self, name: str) -> Element:
        # Only called when normal attribute lookup fails. Dunder lookups
        # (pickle, copy, introspection) must keep failing as usual, and
        # ``_owner`` is guarded to avoid infinite recursion on a
        # half-initialized instance.
        if name == "_owner" or (name.startswith("__") and name.endswith("__")):
            raise AttributeError(name)
        try:
            return self._element(name)
        except KeyError as exc:
            raise AttributeError(str(exc)) from exc

    def __str__(self) -> str:
        return str(self._owner._parse())

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class Element:
    """A reference to an element of the document.

    The ``tag`` attribute is the underlying
    :class:`bs4.element.Tag`, so any Beautiful Soup method works on it.
    """

    def __init__(self, document: Document, tag: Tag) -> None:
        self._document = document
        self.tag = tag

    def append(self, *html: str) -> Element:
        """Append one or more HTML elements as children of this element.

        Each fragment is parsed with Beautiful Soup to validate it, then
        inserted as-is just before this element's end tag, so the rest of
        the document is preserved exactly. Returns ``self`` so calls can
        be chained::

            k.document["head"].append("<a/>").append("<b/>")
        """
        for fragment in html:
            self._document._owner._insert_into(self.tag, fragment)
        return self

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class Kopis:
    """A web application served from a root directory.

    The root directory defaults to the directory of the running script.
    Files in the root directory are served as static assets, and the
    ``document`` is served at ``/``. The document is either an in-memory
    string assigned to ``k.document``, or the ``index.html`` file in the
    root directory. ``k.document`` also gives a :class:`Document` view
    that supports adding HTML elements to existing elements, e.g.
    ``k.document["head"].append("<script src=...></script>")``, and
    :meth:`add_static_file` serves files from anywhere on disk at a
    chosen URL.

    ``use="brython"`` configures the app to run client-side Python code
    with `Brython <https://brython.info>`_: the Brython scripts and the
    modules of the ``kopis`` package are served, and a default document
    loading the Brython scripts is created.
    """

    def __init__(
        self,
        root: str | Path | None = None,
        use: str | None = None,
    ) -> None:
        if root is not None:
            self.root = Path(root).resolve()
        else:
            self.root = _entry_script_dir() or Path.cwd()

        self._document: str | None = None
        self._soup: BeautifulSoup | None = None
        self.app = web.Application()

        # Registered before the static route so that it takes precedence on ``/``.
        self.app.router.add_get("/", self._serve_document)

        self.app.router.add_static("/", self.root, follow_symlinks=True)

        if use not in (None, "brython"):
            raise ValueError(f"unknown value for use: {use!r}")

        if use == "brython":
            self._setup_brython()

    @property
    def document(self) -> Document:
        """A live view of the HTML document served at ``/``."""
        return Document(self)

    @document.setter
    def document(self, value: str) -> None:
        self._document = value
        self._soup = BeautifulSoup(value, "html.parser")

    @property
    def soup(self) -> BeautifulSoup:
        """The document parsed with Beautiful Soup."""
        return self._parse()

    def document_text(self) -> str:
        """The raw HTML text of the document.

        Returns the in-memory document if one was assigned, otherwise
        the contents of ``index.html`` in the root directory.
        """
        if self._document is not None:
            return self._document

        index = self.root / "index.html"
        if not index.is_file():
            raise FileNotFoundError(index)

        return index.read_text()

    def _parse(self) -> BeautifulSoup:
        """The document parsed with Beautiful Soup, cached until changed."""
        if self._soup is None:
            self._soup = BeautifulSoup(self.document_text(), "html.parser")
        return self._soup

    def _insert_into(self, tag: Tag, fragment: str) -> None:
        fragment = fragment.strip()
        if not fragment:
            return

        if tag.name in _VOID_TAGS:
            raise ValueError(f"cannot add children to <{tag.name}>")

        # Parse the fragment with Beautiful Soup to validate it and to
        # confirm it actually contains elements.
        soup = BeautifulSoup(fragment, "html.parser")
        if not any(isinstance(c, Tag) for c in soup.children):
            return

        text = self.document_text()
        offset = _insertion_offset(text, tag)
        self._document = text[:offset] + fragment + text[offset:]
        self._soup = None

    def _setup_brython(self) -> None:
        """Set up the app to run client-side code with Brython.

        Serves the JavaScript files of the installed ``brython`` package
        at ``/brython.js`` and ``/brython_stdlib.js``, serves the Python
        modules of the ``kopis`` package at the URLs Brython's import
        system expects (so e.g. ``from kopis.brython.browser import ...``
        in client code resolves), and initializes a default document with
        the Brython scripts in its ``<head>``.
        """
        import brython  # Optional dependency, required only for use="brython".

        # Locate the JavaScript files shipped with the installed `brython` package.
        brython_path = Path(brython.__file__).parent
        brython_js = brython_path / "data" / "brython.js"
        brython_stdlib_js = brython_path / "data" / "brython_stdlib.js"

        # Serve the brython scripts from where the package installed them.
        self.add_static_file("/brython.js", brython_js)
        self.add_static_file("/brython_stdlib.js", brython_stdlib_js)

        # Serve the kopis package at the URLs Brython's import system expects,
        # so e.g. ``from kopis.brython.browser import ...`` in client.py resolves.
        kopis_path = Path(__file__).resolve().parent
        self.add_static_file("/kopis/__init__.py", kopis_path / "__init__.py")
        self.add_static_file(
            "/kopis/brython/__init__.py", kopis_path / "brython" / "__init__.py"
        )
        self.add_static_file(
            "/kopis/brython/browser.py", kopis_path / "brython" / "browser.py"
        )

        self.document = """
            <html>
                <head>
                    <meta charset="utf-8">
                </head>

                <body>
                </body>
            </html>
        """

        with self.document["head"] as el:
            el.append(
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
            )
            el.append(
                f'<script type="text/javascript" src="{brython_js.name}"></script>'
            )
            el.append(
                f'<script type="text/javascript" src="{brython_stdlib_js.name}"></script>'
            )

    def add_static_file(self, path: str, file_path: str | Path) -> None:
        """Serve a single file at the URL ``path``.

        The explicit route takes precedence over the root static route,
        so files outside the root directory (e.g. data shipped with an
        installed package) can be served directly::

            k.add_static_file("/brython.js", brython_js_path)
        """
        file_path = Path(file_path).resolve()

        async def _handler(_request: web.Request) -> web.FileResponse:
            return web.FileResponse(file_path)

        self.app.router.add_get(path, _handler)

    async def _serve_document(self, _request: web.Request) -> web.Response:
        """Serve the document, rendered as valid HTML.

        The document text (in-memory or ``index.html``) is parsed with
        Beautiful Soup and re-serialized, so the browser always receives
        a canonical, valid form of the document.
        """
        try:
            html = str(self._parse())
        except FileNotFoundError:
            raise web.HTTPNotFound()

        return web.Response(text=html, content_type="text/html")

    def run(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        web.run_app(self.app, host=host, port=port)
