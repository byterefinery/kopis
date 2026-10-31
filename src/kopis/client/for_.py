"""The client-side ``For`` (Brython, in the browser).

The client's half of the unified ``For`` (see
:mod:`kopis.common.for_`): the side with the live DOM, where the loop's
children are rendered, and where a change of the list's signal re-runs
the loop.

The block of the ``with`` statement is captured from the running code
and re-executed once per item of the list: the frame the block runs in
is read at the entry of the ``with`` statement (its line number points
at the ``with`` header, and the frame's code object names the function
the block is in), the function's source is read from the line cache,
and the block's statements — the lines of the function's source that
follow the ``with`` header, indented under it — are compiled to a code
object. Each re-execution binds the loop's ``as`` variable (a
:class:`~kopis.common.for_.Item` of the item and its index) and the
frame's own locals (the names the block reads, like ``k``), and the
elements created in it join the innermost enclosing block (the one
active at the entry of the ``with`` statement) — or the document's body,
if there is no enclosing block.

The block runs once at the entry, with a forgiving item of ``None``
(a *template pass*: the elements it creates are detached, and never
appear in the document), and is re-executed with the items of the list
when the list is read: at once for a list function that returns a
value, and when the coroutine resolves for one that returns one (the
shared signal's getter, on the client). In an active effect scope
(``with k.effect():``) the read of the list function is tracked, as a
signal read in a component is: a change of the signal it reads re-reads
the list and re-renders the loop, in place. A re-execution supersedes
the previous one, and a pending read of a superseded re-execution is
dropped: the reads' resolutions are not ordered among themselves, and
the list of the newest read wins.
"""

import linecache
import re
import sys
from collections.abc import Callable
from inspect import iscoroutine
from typing import Any

from browser import aio, document

from ..common.for_ import Item
from ..common.signal import _effect_scope
from .dom import _native_create_element, _scope

__all__ = ["For"]

# The ``as`` target of the ``with`` header: the last name before the
# header's final colon (``with For(get_x) as item:``), bare or in
# parentheses (``with For(get_x) as (item):``).
_AS_TARGET = re.compile(r"as\s*\(?([A-Za-z_][A-Za-z0-9_]*)\)?\s*$")


def _indent(line: str) -> int:
    """The number of leading whitespace characters of ``line``."""
    return len(line) - len(line.lstrip())


def _function_lines(code: Any) -> tuple[list[str], int]:
    """The source lines of the function ``code`` is the code of, and the
    1-based number of its first line in the file (the ``def``'s line).

    The line cache serves the source under the code object's filename
    (the main script's, with Brython's ``#__main__`` mark, which it
    handles, as with any module's); the function's block is the lines
    indented under its ``def``. A module-level code object (``<module>``)
    is the file itself, from its first line.
    """
    lines = linecache.getlines(code.co_filename)
    if code.co_name == "<module>" or not lines:
        return list(lines), 1
    first = code.co_firstlineno
    if not isinstance(first, int) or first < 1 or first > len(lines):
        return list(lines), 1
    def_indent = _indent(lines[first - 1])
    end = first
    while end < len(lines):
        line = lines[end]
        if line.strip() and _indent(line) <= def_indent:
            break
        end += 1
    return list(lines[first - 1 : end]), first


def _with_header_end(lines: list[str], with_line: int) -> int:
    """The 1-based number of the last line of the ``with`` header that
    starts at ``with_line``: the first line, from there, whose
    parentheses are balanced (counted from the header's start) and
    whose comment-free text ends with the header's colon. A one-line
    header is its own last line, as a multi-line header's is the line
    of its closing parenthesis (and ``as`` target)."""
    balance = 0
    for line_no in range(with_line, len(lines) + 1):
        line = lines[line_no - 1]
        for char in line:
            if char in "([{":
                balance += 1
            elif char in ")]}":
                balance -= 1
        text = line.split("#", 1)[0].strip()
        if balance <= 0 and text.endswith(":"):
            return line_no
    return with_line  # no closing line: treat the header as one line


def _with_body(lines: list[str], with_line: int) -> tuple[str, str | None]:
    """The source of the body of the ``with`` statement starting at
    ``with_line`` (1-based, within ``lines``), dedented, and the name of
    its ``as`` variable (``None`` if it has none)."""
    header_end = _with_header_end(lines, with_line)
    header = " ".join(
        line.split("#", 1)[0].strip() for line in lines[with_line - 1 : header_end]
    )
    header = header.removesuffix(":")
    match = _AS_TARGET.search(header)
    as_name = match.group(1) if match else None
    indent = _indent(lines[with_line - 1])
    # ``header_end`` is the 1-based number of the header's last line, so
    # the body's first line sits at the 0-based index ``header_end``.
    start = header_end
    end = start
    while end < len(lines):
        line = lines[end]
        if line.strip() and _indent(line) <= indent:
            break
        end += 1
    body = lines[start:end]
    indents = [_indent(line) for line in body if line.strip()]
    common = min(indents) if indents else 0
    source = "".join(line[common:] if line.strip() else "" for line in body)
    return source, as_name


class For:
    """A reactive ``for`` loop of the client (see the module docstring).

    The argument is a list function — a function that returns the list
    to iterate over (a signal's getter, a shared signal's getter, or
    any function). The block of the ``with`` statement is the loop's
    body, and its elements join the innermost enclosing block (the one
    active at the entry of the ``with`` statement) — or the document's
    body, if there is none. In an active effect scope (``with
    k.effect():``) the read of the list function is tracked: a change
    of the signal it reads re-reads the list, and re-renders the loop's
    children in place (the block is re-executed once per item)."""

    list_fn: Callable[[], Any]
    scope: Any | None
    parent: Any
    dummy: Any
    body: Any
    as_name: str | None
    globals: Any
    locals: dict[str, Any]
    nodes: list[Any]
    generation: int

    def __init__(self, list_fn: Callable[[], Any]) -> None:
        self.list_fn = list_fn
        self.scope = None
        self.parent = None
        self.dummy = None
        self.body = None
        self.as_name = None
        self.globals = None
        self.locals = {}
        self.nodes = []
        self.generation = 0

    def __enter__(self) -> Item:
        """Enter the loop: capture the block's source (and the frame it
        runs in), read the list (tracked, in an active effect scope),
        and hand out the template pass's item (a forgiving item of
        ``None`` — the elements the block creates with it are detached,
        and never appear in the document)."""
        frame = sys._getframe(1)
        self._capture(frame)
        # The elements of the re-executions join the innermost enclosing
        # block (or the document's body, if there is none).
        self.parent = _scope[-1] if _scope else None
        # The template pass's elements are detached: they join this
        # dummy element, which is never attached to the document.
        self.dummy = _native_create_element("div")
        _scope.append(self.dummy)
        scope = _effect_scope()
        self.scope = scope
        value = (
            scope.track(self.list_fn, self._update)
            if scope is not None
            else self.list_fn()
        )
        self._resolve(value)
        return Item(0, None)

    def __exit__(self, *exc_info: object) -> bool:
        """Leave the block. The template pass's dummy element is no
        longer the innermost block element. Exceptions are not
        suppressed."""
        if _scope and _scope[-1] is self.dummy:
            _scope.pop()
        return False

    def _capture(self, frame: Any) -> None:
        """Capture the source of the block (to re-execute it once per
        item), and the frame's globals and locals (the names the block
        reads)."""
        code = frame.f_code
        lines, first = _function_lines(code)
        with_line = frame.f_lineno - first + 1
        # The frame's line number points at the ``with`` header (its
        # first line, even when the header spans lines); if it is off,
        # find the header's line around it.
        if not (
            isinstance(with_line, int)
            and 1 <= with_line <= len(lines)
            and lines[with_line - 1].strip().startswith("with")
        ):
            found = None
            for line_no in range(
                max(1, with_line - 16), min(len(lines), with_line + 16) + 1
            ):
                if lines[line_no - 1].strip().startswith("with"):
                    found = line_no
                    break
            if found is None:
                raise RuntimeError(
                    f"For: cannot capture the source of the with block"
                    f" (no function source for {code.co_filename!r})"
                )
            with_line = found
        source, as_name = _with_body(lines, with_line)
        self.body = compile(source, code.co_filename, "exec")
        self.as_name = as_name
        self.globals = frame.f_globals
        self.locals = self._snapshot(frame)

    @staticmethod
    def _snapshot(frame: Any) -> dict[str, Any]:
        """A copy of the frame's local names (the block's free names:
        the ones it reads, like ``k``)."""
        try:
            return dict(frame.f_locals)
        except Exception:  # noqa: BLE001 - brython's f_locals can be a JS object
            return {}

    def _update(self) -> None:
        """The observer of a change of the list's signal: the list is
        re-read (re-tracked, as a solidjs effect re-tracks on every
        re-run), and the loop is re-rendered with the new list."""
        scope = self.scope
        value = (
            scope.track(self.list_fn, self._update)
            if scope is not None
            else self.list_fn()
        )
        self._resolve(value)

    def _resolve(self, value: Any) -> None:
        """Render the loop with the list ``value`` — at once for a value,
        and when the coroutine resolves for a coroutine of one. A read
        supersedes the previous one: a pending resolution of a
        superseded read is dropped, so the list of the newest read wins
        (the reads' resolutions are not ordered among themselves)."""
        self.generation += 1
        generation = self.generation
        if iscoroutine(value):

            async def fill() -> None:
                try:
                    items = list(await value)
                except Exception as exc:  # noqa: BLE001 - a failed read keeps the loop alive
                    print(f"kopis: a For list read failed: {exc}")
                    return
                if generation != self.generation:
                    # Superseded by a newer read: the newer list wins.
                    return
                try:
                    self._render(items)
                except Exception as exc:  # noqa: BLE001 - a failed render keeps the loop alive
                    print(f"kopis: a For render failed: {exc}")

            aio.run(fill())
            return
        self._render(list(value))

    def _render(self, items: list[Any]) -> None:
        """The items' children take the place of the loop's current
        children: the old children are removed, and the block is
        re-executed once per item (its elements join the parent, in the
        brython way)."""
        parent = self.parent if self.parent is not None else document.body
        for node in self.nodes:
            if node.parentNode is parent:
                parent.removeChild(node)
        self.nodes = []
        before = len(list(parent.childNodes))
        _scope.append(parent)
        try:
            for index, item in enumerate(items):
                locals = dict(self.locals)
                if self.as_name is not None:
                    locals[self.as_name] = Item(index, item)
                exec(self.body, self.globals, locals)  # noqa: S102
        finally:
            if _scope and _scope[-1] is parent:
                _scope.pop()
        self.nodes = list(parent.childNodes)[before:]

    def __repr__(self) -> str:
        return f"<For {len(self.nodes)} child(ren)>"
