"""Kopis: pure-Python web development (client side).

This is the client-side half of the ``kopis`` package: it runs in the
browser under Brython. It shares its API with the server-side half (the
``kopis.server`` subpackage); only the implementation differs: no web
server, no root directory. ``k.run()`` and ``k.add_static_file()`` are
no-ops here; ``k.document`` is a live view of the browser document; and
``k.bind``/``k.rpc`` implement the RPC client half.

Calls from the server to functions registered with :meth:`Kopis.bind`
arrive over a Server-Sent Events stream (``EventSource`` on
``/__kopis__/rpc/events``); their results are posted back to the server
(``/__kopis__/rpc/results``) as soon as they are ready. All HTTP goes
through ``browser.aio`` and the browser's implicit event loop drives
everything; ``aio.run`` starts a coroutine without blocking.
"""

__all__ = ["Document", "Element", "Kopis", "RpcError", "aio", "document", "javascript"]

import inspect
import json
import platform
from collections.abc import Callable
from typing import Any, Self

try:
    from dataclasses import asdict, is_dataclass
except ImportError:  # Interpreter without dataclasses support.
    asdict = None
    is_dataclass = None

if platform.python_implementation() == "Brython":
    # Client: `browser` and `javascript` are Brython built-in modules.
    from browser import aio, document, window
    import javascript
else:
    # Server: `aio`, `document`, `window`, and `javascript` are Brython-only;
    # stand-ins keep this subpackage importable under CPython.
    from unittest.mock import MagicMock

    aio = MagicMock()
    document = MagicMock()
    window = MagicMock()
    javascript = MagicMock()


# --- Wire format, shared with the server-side `kopis` subpackage -----------
#
# RPC messages are JSON. Custom types participate by defining a
# ``to_json()`` method that returns plain JSON-able data; dataclasses and
# objects with a ``__dict__`` are converted to a dict of their attributes;
# anything else falls back to ``str()``. Neither side assumes the other
# side has the same types — a value always arrives on the receiving end
# as plain JSON data (dicts, lists, strings, numbers).


class RpcError(Exception):
    """Raised when a remote function call failed on the other side."""

    def __init__(self, type: str, message: str) -> None:
        super().__init__(f"{type}: {message}")
        self.type = type
        self.message = message


def _convert(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    to_json = getattr(value, "to_json", None)
    if callable(to_json):
        return _convert(to_json())
    if (
        is_dataclass is not None
        and asdict is not None
        and is_dataclass(value)
        and not isinstance(value, type)
    ):
        return _convert(asdict(value))
    if isinstance(value, dict):
        return {key: _convert(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_convert(item) for item in value]
    if hasattr(value, "__dict__"):
        return _convert(vars(value))
    return str(value)


def encode(value: object) -> str:
    """Serialize ``value`` to a JSON string, converting custom types to plain data."""
    return json.dumps(_convert(value))


def decode(text: str) -> Any:
    """Parse a JSON string into plain Python values."""
    return json.loads(text)


RPC_URL = "/__kopis__/rpc"
EVENTS_URL = "/__kopis__/rpc/events"
RESULTS_URL = "/__kopis__/rpc/results"
_JSON = {"Content-Type": "application/json"}
_RETRY_DELAY = 1.0  # pause before retrying a failed results POST
_DONE_CAP = 1000  # completed calls remembered, to deduplicate replayed calls


class Element:
    """A reference to an element of the browser document.

    The unified document API works the same way as on the server:
    :meth:`append` adds HTML elements, ``<=`` adds content, and
    :meth:`bind` attaches an event handler. Any other attribute is
    delegated to the underlying DOM element, so all DOM properties and
    methods (``id``, ``innerHTML``, ``value``, ...) work as-is.
    """

    def __init__(self, element: Any) -> None:
        self._element = element

    def append(self, *html: str) -> Element:
        """Append one or more HTML elements as children of this element.

        Each fragment is inserted as-is just before this element's end
        tag. Returns ``self`` so calls can be chained::

            k.document.body.append("<a/>").append("<b/>")
        """
        for fragment in html:
            fragment = fragment.strip()
            if not fragment:
                continue
            self._element.insertAdjacentHTML("beforeend", fragment)
        return self

    def bind(self, event: str, handler: Callable) -> Any:
        """Bind an event handler to this element (delegates to the DOM)."""
        return self._element.bind(event, handler)

    def __le__(self, content: object) -> None:
        """Append ``content`` as a child of this element."""
        self._element <= content  # noqa: B015 (Brython's <= adds a child)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def __getattr__(self, name: str) -> Any:
        # Only called when normal attribute lookup fails. Dunder lookups
        # (pickle, copy, introspection) must keep failing as usual, and
        # ``_element`` is guarded to avoid infinite recursion on a
        # half-initialized instance.
        if name == "_element" or (name.startswith("__") and name.endswith("__")):
            raise AttributeError(name)
        return getattr(self._element, name)


class Document:
    """A live view of the browser document.

    The unified document API works the same way as on the server: look up
    an element by tag name with either subscripting or attribute access,
    or by CSS selector with :meth:`querySelector`; both return an
    :class:`Element`::

        with k.document.body as el:
            el.append("<button id=...></button>")
        k.document.querySelector("#btn0").bind("click", handler)
    """

    def __init__(self, document: Any) -> None:
        self._document = document

    def _element(self, name: str) -> Element:
        try:
            return Element(getattr(self._document, name))
        except AttributeError as exc:
            raise AttributeError(f"no <{name}> element in the document") from exc

    def querySelector(self, selector: str) -> Element | None:
        """Return the first element matching ``selector``, or ``None``."""
        element = self._document.querySelector(selector)
        if element is None:
            return None
        return Element(element)

    def __getitem__(self, name: str) -> Element:
        return self._element(name)

    def __getattr__(self, name: str) -> Element:
        # Only called when normal attribute lookup fails. Dunder lookups
        # (pickle, copy, introspection) must keep failing as usual, and
        # ``_document`` is guarded to avoid infinite recursion on a
        # half-initialized instance.
        if name == "_document" or (name.startswith("__") and name.endswith("__")):
            raise AttributeError(name)
        return self._element(name)

    def __le__(self, content: object) -> None:
        """Append ``content`` to the document (its body)."""
        self._document <= content  # noqa: B015 (Brython's <= adds to the document)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class _Rpc:
    """Proxy for ``k.rpc``: ``k.rpc.name(args)`` calls the server's function."""

    def __init__(self, owner: Kopis) -> None:
        self._owner = owner

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        async def call(*args: object, **kwargs: object) -> object:
            body = encode({"method": name, "args": list(args), "kwargs": kwargs})
            req = await aio.post(RPC_URL, data=body, headers=_JSON)
            msg = decode(req.data)
            if "error" in msg:
                err = msg["error"]
                raise RpcError(err.get("type", "Error"), err.get("message", ""))
            return msg["result"]

        return call


class Kopis:
    """A kopis application, client side.

    Instantiate it in app code (the same code runs on the server, where
    :meth:`run` starts the web server, and in the browser, where it is a
    no-op)::

        from kopis import Kopis
        k = Kopis(use="brython")

        @k.bind
        async def client_fn(x): ...         # callable from the server

        result = await k.rpc.server_fn(x)   # calls a server function

    Calls to the functions registered with :meth:`bind` arrive over a
    Server-Sent Events stream; their results are posted back to the server
    as soon as they are ready.
    """

    def __init__(self, root: object = None, use: str | None = None) -> None:
        if use not in (None, "brython"):
            raise ValueError(f"unknown value for use: {use!r}")
        self._bound: dict[str, Callable[..., Any]] = {}
        self._results: list[dict] = []  # results not yet sent to the server
        self._done: dict[int, dict] = {}  # completed call id -> result payload
        self._sending = False
        self.rpc = _Rpc(self)
        # `.new` calls the JS constructor with the `new` operator.
        self._source = window.EventSource.new(EVENTS_URL)
        self._source.bind("call", self._on_call)
        self._source.bind("error", self._on_error)

    @property
    def document(self) -> Document:
        """A live view of the browser document."""
        return Document(document)

    def bind(self, func) -> Callable[..., Any]:
        """Register a function so the other side can call it by name."""
        self._bound[func.__name__] = func
        return func

    def add_static_file(self, path: str, file_path: object) -> None:
        """No-op on the client: files are served by the server."""

    def run(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        """No-op on the client: the web server runs on the server side."""

    def close(self) -> None:
        """Close the event stream to the server."""
        self._source.close()

    def _on_call(self, event: Any) -> None:
        """Handle a ``call`` event pushed by the server."""
        try:
            call = decode(event.data)
        except Exception:  # noqa: BLE001 - a bad event must not kill the stream
            return
        done = self._done.get(call.get("id"))
        if done is None:
            aio.run(self._run_call(call))
        else:
            # Duplicate delivery: the server replays calls until their result
            # is received, so a reconnect can re-send one we already ran.
            # Re-send the stored result instead of running it again.
            self._results.append(done)
        aio.run(self._flush_results())

    def _on_error(self, event: Any) -> None:
        # EventSource reconnects on its own; the server replays any calls
        # still awaiting a result, so no call is lost.
        print("kopis: event stream error, reconnecting")

    async def _flush_results(self) -> None:
        """Post pending results to the server.

        One flush runs at a time; concurrent completions append to
        ``self._results`` and are picked up by the running loop.
        """
        if self._sending:
            return
        self._sending = True
        try:
            while self._results:
                n = len(self._results)
                body = encode({"results": self._results[:n]})
                try:
                    await aio.post(RESULTS_URL, data=body, headers=_JSON)
                except Exception as exc:  # noqa: BLE001 - retry until it goes through
                    print("kopis: sending results failed:", exc)
                    await aio.sleep(_RETRY_DELAY)
                    continue
                del self._results[:n]
        finally:
            self._sending = False
            if self._results:
                aio.run(self._flush_results())

    async def _run_call(self, call: dict) -> None:
        bound = self._bound.get(call.get("method"))
        if bound is None:
            payload = {
                "id": call["id"],
                "error": {
                    "type": "NameError",
                    "message": f"no function {call.get('method')!r} bound on the client",
                },
            }
        else:
            try:
                result = bound(*call.get("args", []), **call.get("kwargs", {}))
                if inspect.iscoroutine(result):
                    result = await result
                payload = {"id": call["id"], "result": result}
            except Exception as exc:  # noqa: BLE001 - report any failure to the server
                payload = {
                    "id": call["id"],
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
        self._done[call["id"]] = payload
        while len(self._done) > _DONE_CAP:
            del self._done[next(iter(self._done))]
        self._results.append(payload)
        aio.run(self._flush_results())
