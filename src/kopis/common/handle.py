"""``Handle`` — a stand-in for a live object on the other side.

A value that cannot be serialized does not travel, and sending it
raises — the developer wraps the value in a :class:`Handle`
instead: the wrap is ``Kopis.handle``, and ``Kopis.get_handle`` makes
a handle to any object (picklable or not) for sending. The live object
stays alive on the side where it is, and the handle travels freely
between server and client, in either direction, as many times as
needed.

A handle prints as ``<Handle local ...>`` or ``<Handle remote ...>``
— ``local`` when this side owns the live object, ``remote`` when it
came from the other side — followed by the true representation of the
live object, which the owning side computes (a call of its ``__repr__``)
when the handle is made. The string travels with the handle, so the
receiving side prints it locally, with no round trip.

An ``Handle`` is a magic type: every operation on it is accepted,
and sent over the wire to the side that owns the live object. It is
the owner — the original place where the live object is — that applies
the operation and decides whether it can be performed; a failure there
comes back as an :class:`~kopis.common.RpcError`. The live object may
be on this side (the op applies at once) or on the other side (a round
trip); in both cases the call reads naturally, mirroring the live
object: a sync function, method, or attribute is invoked and returns
its value, and a coroutine method is invoked and awaited::

    value = handle.attr           # read an attribute
    result = handle.method(a)     # call a sync method
    result = await handle.method(a)   # call a coroutine method
    item = handle[key]            # subscript
    handle.attr = value           # set an attribute
    handle[key] = value           # set an item
    del handle[key]               # delete an item
    async for x in handle: ...    # iterate

How the round trip happens depends on the side: when the live object
is on this side, the op applies at once (no wire at all); when it is
on the other side, the server — which runs the calling code off its
event loop — performs the round trip and blocks the calling thread,
while the client (whose single browser thread cannot block) returns
an awaitable future instead, so there ``await handle.method(a)`` and
``await handle.attr`` are the forms that work.

The handle's own state (id, owner) is private, so it never shadows an
attribute of the live object: ``await handle.id`` reads the live
object's ``id``, as if the handle were the object itself.
Operation results come back through the same serialization, so a
result that is itself unserializable cannot travel: the failure is
reported to the other side as the error of the operation (an
:class:`~kopis.common.RpcError` on the awaiting side), and the value
stays alive on the side where it is.

A handle that comes back to the side where it was made is unwrapped
there, as an argument or result of a call or op: it is replaced by
the live object it wraps — the object is already on that side, so it
is passed as is.
"""

import platform
from typing import Any

__all__ = ["Handle"]

_brython_wrap: Any = None  # the promise wrap function, cached


def _stop_iteration() -> None:
    """The ``__next__`` of the wrapped promise.

    Never driven — brython's ``await`` drives the native promise
    through ``then`` — but brython requires the object returned from
    ``__await__`` to expose ``__next__``, so it must be there.
    """
    raise StopIteration


def _brython_promise_wrap() -> Any:
    """Brython only: a function wrapping an ``aio.Future`` (a native
    Javascript promise) in a native ``Promise`` that brython's
    ``await`` drives.

    Brython compiles ``await`` to a native Javascript await of the
    object ``__await__`` returns: the object must expose ``__next__``
    to pass brython's check, and it must be a native thenable — a
    ``Promise`` — for the native await to actually wait on it. A
    plain value (a locally-owned op applied at once) is resolved
    directly.
    """
    global _brython_wrap
    if _brython_wrap is None:
        from browser import window

        def _wrap(fut: Any) -> Any:
            def _executor(resolve: Any, reject: Any) -> None:
                if fut is None or not hasattr(fut, "then"):
                    # A plain value (a locally-owned op applied at
                    # once): resolve it directly.
                    resolve(fut)
                else:
                    fut.then(resolve, reject)

            promise = window.Promise.new(_executor)
            promise.__next__ = _stop_iteration
            return promise

        _brython_wrap = _wrap
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


class HandleAttr:
    """``handle.attr``: a method of the live object (or an attribute
    read, on the client, where the read cannot block the browser
    thread).

    Calling it invokes the method on the live object (``handle.attr(
    *args, **kwargs)``): the result of a sync method is returned
    directly, and the result of a coroutine method is an awaitable. On
    the client, awaiting it reads the attribute on the live object
    (``await handle.attr``).
    """

    def __init__(self, handle: Handle, name: str) -> None:
        self.handle = handle
        self.name = name

    def __reduce__(self):
        # The stand-in travels like a handle: its handle travels (bound
        # again by the receiver when it decodes the message), and its
        # name is plain data.
        return (HandleAttr, (self.handle, self.name))

    def __call__(self, *args: object, **kwargs: object) -> Any:
        return self.handle._kopis._handle_op(
            self.handle, "call", self.name, args, kwargs
        )

    def __await__(self):
        result = self.handle._kopis._handle_op(self.handle, "getattr", self.name)
        if platform.python_implementation() == "Brython":
            # The client's remote op returns a future (a native
            # promise): brython's await drives it natively.
            return _brython_promise_wrap()(result)
        if hasattr(result, "_asyncio_future_blocking"):
            return _await_future(result)

        def _value(value: Any) -> Any:
            yield from ()
            return value

        return _value(result)

    def __repr__(self) -> str:
        return f"<Handle attribute {self.name!r}>"


class AsyncList:
    """An async iterator over the items of the live object (the result
    of an ``iter`` operation on it)."""

    def __init__(self, items: list[Any]) -> None:
        self.items = list(items)
        self.index = 0

    def __aiter__(self) -> AsyncList:
        return self

    async def __anext__(self) -> Any:
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


class Handle[T]:
    """A stand-in for a live object that does not travel.

    The live object stays on the side that owns it (``owner_side``, and
    ``owner_id`` — the client id — when that side is a client tab), and
    this handle is what travels. ``true_repr`` is the true
    representation of the live object (a call of its ``__repr__``, made
    by the owning side when the handle is made), so this side prints
    the handle as ``<Handle local ...>`` or ``<Handle remote ...>``
    — ``local`` when this side owns the live object, ``remote`` when it
    came from the other side — without a round trip.

    The type parameter is optional and documents only: it names the
    type of the live object the handle points at (``Handle[Point]``),
    while the bare ``Handle`` is a handle to any object. It is not
    checked at runtime.

    The handle's own state is private (``_id``, ``_owner_side``,
    ``_owner_id``, ``_true_repr``), so it never shadows an attribute
    of the live object.

    The handle is bound to a ``Kopis`` (``_kopis`` is set when the
    handle is made, and re-set when the receiving side decodes the
    message); every operation on the handle goes through that side's
    :meth:`KopisBase._handle_op`, which applies it locally when this
    side owns the live object, and sends it to the owner otherwise.

    When the handle comes back to the side where it was made, it is
    unwrapped there — the side passes its live object instead; see
    the module docstring.
    """

    _id: int
    _owner_side: str
    _owner_id: str | None
    _true_repr: str
    _kopis: Any  # the Kopis of the side that holds this handle (None until bound)

    def __init__(
        self,
        id: int,
        owner_side: str,
        owner_id: str | None = None,
        true_repr: str = "",
    ) -> None:
        # via object.__setattr__: the __setattr__ below routes public
        # names to the live object (the own state must stay out of it)
        object.__setattr__(self, "_id", id)
        object.__setattr__(self, "_owner_side", owner_side)
        object.__setattr__(self, "_owner_id", owner_id)
        object.__setattr__(self, "_true_repr", true_repr)
        object.__setattr__(self, "_kopis", None)

    def __reduce__(self):
        # The handle itself must travel: pickle without the (huge,
        # unpicklable) ``_kopis`` binding; a fresh, unbound instance
        # arrives, and the receiving side re-binds it when it decodes
        # the message.
        return (
            Handle,
            (self._id, self._owner_side, self._owner_id, self._true_repr),
        )

    def __repr__(self) -> str:
        # Local print: the true repr of the live object travels with the
        # handle (the owner computed it when the handle was made), so
        # no round trip is needed.
        if self._kopis is not None and self._owner_side == self._kopis.side:
            side = "local"
        else:
            side = "remote"
        return f"<Handle {side} {self._true_repr}>"

    __str__ = __repr__

    # -- the magic interface: every operation goes to the owner ---------

    def __getattr__(self, name: str) -> Any:
        # A (public) attribute of the live object: its value for a data
        # attribute, a call stand-in (HandleAttr) for a method — the
        # getattr op is performed by this side's Kopis, which applies
        # it at once when this side owns the live object and travels it
        # to the owner otherwise.
        if name.startswith("_"):
            raise AttributeError(name)
        return self._kopis._handle_getattr(self, name)

    def __setattr__(self, name: str, value: object) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        self._send_mutation("setattr", name, (value,))

    def __call__(self, *args: object, **kwargs: object) -> Any:
        # Call the live object itself: a future of its result.
        return self._kopis._handle_op(self, "call", None, args, kwargs)

    def __getitem__(self, key: object) -> Any:
        # The item: its value for a sync ``__getitem__``, an awaitable
        # if the live object's is a coroutine.
        return self._kopis._handle_op(self, "getitem", None, (key,))

    def __setitem__(self, key: object, value: object) -> None:
        self._send_mutation("setitem", None, (key, value))

    def __delitem__(self, key: object) -> None:
        self._send_mutation("delitem", None, (key,))

    def __aiter__(self) -> AsyncList:
        items = self._kopis._handle_op(self, "iter")
        return AsyncList(items)

    def _send_mutation(self, op: str, name: str | None, args: tuple) -> None:
        """Perform a mutation (``setattr`` / ``setitem`` / ``delitem``).

        The owner applies it: on the server the mutation is synchronous
        (the round trip completes before the assignment returns, and a
        failure raises); on the client it is fire and forget (a
        synchronous dunder cannot await the outcome, so any failure
        there goes unreported).
        """
        self._kopis._handle_op(self, op, name, args, {})
