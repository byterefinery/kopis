"""``RPCHandle`` — a stand-in for a live object on the other side.

A value that cannot be serialized — pickled on the sender side, or
unpickled on the receiver side — does not travel: it stays alive where
it is, and an :class:`RPCHandle` pointing at it is sent instead. The
wrap is ``Kopis.handle``; ``Kopis.get_handle`` makes an explicit handle
to any object (picklable or not) for sending. Handles travel freely
between server and client, in either direction, as many times as
needed.

A handle prints as ``<RPCHandle local ...>`` or ``<RPCHandle remote ...>``
— ``local`` when this side owns the live object, ``remote`` when it
came from the other side — followed by the true representation of the
live object, which the owning side computes (a call of its ``__repr__``)
when the handle is made. The string travels with the handle, so the
receiving side prints it locally, with no round trip.

An ``RPCHandle`` is a magic type: every operation on it is accepted,
and sent over the wire to the side that owns the live object. It is
the owner — the original place where the live object is — that applies
the operation and decides whether it can be performed; a failure there
comes back as an :class:`~kopis.common.RpcError`. Since the round trip
is asynchronous, value-returning operations are awaitable::

    value = await handle.attr         # read an attribute
    result = await handle.method(a)   # call a method
    item = await handle[key]          # subscript
    handle.attr = value               # set an attribute (fire and forget)
    handle[key] = value               # set an item (fire and forget)
    del handle[key]                   # delete an item (fire and forget)
    async for x in handle: ...        # iterate

The handle's own state (id, owner, reason) is private, so it never
shadows an attribute of the live object: ``await handle.id`` reads the
live object's ``id``, as if the handle were the object itself.
Operation results come back through the same serialization, so a
result that is itself unserializable arrives as another ``RPCHandle``
(still owned by the side that produced it).
"""

from __future__ import annotations

import platform
from typing import Any

__all__ = ["RPCHandle"]

#: Brython only: a native Javascript ``Promise`` subclass that brython's
#: ``await`` drives (see :func:`_brython_promise_wrap`).
_PROMISE_WRAP_JS = (
    "(function () {"
    "  class P extends Promise {"
    "    constructor(executor) { super(executor) }"
    "    __next__() { throw new Error('StopIteration') }"
    "  }"
    "  return function (fut) {"
    "    return new P(function (resolve, reject) {"
    "      fut.then(resolve, reject)"
    "    })"
    "  }"
    "})()"
)

_brython_wrap: Any = None  # the ``_PROMISE_WRAP_JS`` function, cached


def _brython_promise_wrap() -> Any:
    """Brython only: a function wrapping an ``aio.Future`` (a native
    Javascript promise) in a native ``Promise`` subclass.

    Brython's ``await`` only drives native thenables, and requires the
    object returned from ``__await__`` to expose ``__next__`` — a
    subclass of ``Promise`` satisfies both.
    """
    global _brython_wrap
    if _brython_wrap is None:
        from browser import window

        _brython_wrap = window.eval(_PROMISE_WRAP_JS)
    return _brython_wrap


def _await_future(future: Any):
    """The CPython ``__await__`` protocol: yield the future, so the
    runtime waits for it.

    The future is marked as yielded through ``__await__``, as
    ``asyncio.Future.__await__`` does, so that an ``asyncio`` task
    accepts the yield.
    """
    if hasattr(future, "_asyncio_future_blocking"):
        future._asyncio_future_blocking = True
    yield future
    return future.result()


class _HandleAttr:
    """``handle.attr``: an attribute of the live object, or a call on it.

    Awaiting it reads the attribute on the live object (``await
    handle.attr``); calling it invokes it there (``await
    handle.attr(*args, **kwargs)``), and in both cases returns a future
    of the result, settled by the owner side.
    """

    def __init__(self, handle: RPCHandle, name: str) -> None:
        self._handle = handle
        self._name = name

    def __call__(self, *args: object, **kwargs: object) -> Any:
        return self._handle._kopis._handle_op(
            self._handle, "call", self._name, args, kwargs
        )

    def __await__(self):
        future = self._handle._kopis._handle_op(self._handle, "getattr", self._name)
        if platform.python_implementation() == "Brython":
            return _brython_promise_wrap()(future)
        return _await_future(future)

    def __repr__(self) -> str:
        return f"<RPCHandle attribute {self._name!r}>"


class _AsyncList:
    """An async iterator over the items of the live object (the result
    of an ``iter`` operation on it)."""

    def __init__(self, future: Any) -> None:
        self._items: list[Any] | None = None
        self._index = 0
        self._future = future

    def __aiter__(self) -> _AsyncList:
        return self

    async def __anext__(self) -> Any:
        if self._items is None:
            self._items = list(await self._future)
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


class RPCHandle[T]:
    """A stand-in for a live object that does not travel.

    The live object stays on the side that owns it (``owner_side``, and
    ``owner_id`` — the client id — when that side is a client tab), and
    this handle is what travels. ``true_repr`` is the true
    representation of the live object (a call of its ``__repr__``, made
    by the owning side when the handle is made), so this side prints
    the handle as ``<RPCHandle local ...>`` or ``<RPCHandle remote ...>``
    — ``local`` when this side owns the live object, ``remote`` when it
    came from the other side — without a round trip. ``reason`` is the
    string of the exception that made the value unserializable
    (``None`` for an explicit handle).

    The type parameter is optional and documents only: it names the
    type of the live object the handle points at (``RPCHandle[Point]``),
    while the bare ``RPCHandle`` is a handle to any object. It is not
    checked at runtime.

    The handle's own state is private (``_id``, ``_owner_side``,
    ``_owner_id``, ``_true_repr``, ``_reason``), so it never shadows an
    attribute of the live object.

    The handle is bound to a ``Kopis`` (``_kopis`` is set when the
    handle is made, and re-set when the receiving side decodes the
    message); every operation on the handle goes through that side's
    :meth:`KopisBase._handle_op`, which applies it locally when this
    side owns the live object, and sends it to the owner otherwise.
    """

    _id: int
    _owner_side: str
    _owner_id: str | None
    _true_repr: str
    _reason: str | None
    _kopis: Any  # the Kopis of the side that holds this handle (None until bound)

    def __init__(
        self,
        id: int,
        owner_side: str,
        owner_id: str | None = None,
        true_repr: str = "",
        reason: str | None = None,
    ) -> None:
        object.__setattr__(self, "_id", id)
        object.__setattr__(self, "_owner_side", owner_side)
        object.__setattr__(self, "_owner_id", owner_id)
        object.__setattr__(self, "_true_repr", true_repr)
        object.__setattr__(self, "_reason", reason)
        object.__setattr__(self, "_kopis", None)

    def __reduce__(self):
        # The handle itself must travel: pickle without the (huge,
        # unpicklable) ``_kopis`` binding; a fresh, unbound instance
        # arrives, and the receiving side re-binds it when it decodes
        # the message.
        return (
            RPCHandle,
            (
                self._id,
                self._owner_side,
                self._owner_id,
                self._true_repr,
                self._reason,
            ),
        )

    def __repr__(self) -> str:
        # Local print: the true repr of the live object travels with the
        # handle (the owner computed it when the handle was made), so
        # no round trip is needed.
        if self._kopis is not None and self._owner_side == self._kopis.side:
            side = "local"
        else:
            side = "remote"
        return f"<RPCHandle {side} {self._true_repr}>"

    __str__ = __repr__

    # -- the magic interface: every operation goes to the owner ---------

    def __getattr__(self, name: str) -> _HandleAttr:
        # Any (public) attribute of the live object; awaiting it reads
        # it there, calling it invokes it there.
        if name.startswith("_"):
            raise AttributeError(name)
        return _HandleAttr(self, name)

    def __setattr__(self, name: str, value: object) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        self._send_mutation("setattr", name, (value,))

    def __call__(self, *args: object, **kwargs: object) -> Any:
        # Call the live object itself: a future of its result.
        return self._kopis._handle_op(self, "call", None, args, kwargs)

    def __getitem__(self, key: object) -> Any:
        # A future of the item: ``await handle[key]``.
        return self._kopis._handle_op(self, "getitem", None, (key,))

    def __setitem__(self, key: object, value: object) -> None:
        self._send_mutation("setitem", None, (key, value))

    def __delitem__(self, key: object) -> None:
        self._send_mutation("delitem", None, (key,))

    def __aiter__(self) -> _AsyncList:
        return _AsyncList(self._kopis._handle_op(self, "iter"))

    def _send_mutation(self, op: str, name: str | None, args: tuple) -> None:
        """Send a mutation (``setattr`` / ``setitem`` / ``delitem``).

        Mutations are fire and forget: the owner applies them; since a
        synchronous dunder cannot await the outcome, any failure there
        goes unreported.
        """
        self._kopis._handle_op(self, op, name, args, {})
