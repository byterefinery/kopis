"""``Effect`` — a reactive scope, in the spirit of solidjs's
``createEffect``.

In solidjs, ``createEffect(fn)`` runs ``fn``, observes the signals read
during the run, and re-runs the read's update whenever one of those
signals changes. This is the same primitive, in pure Python, so it runs
unmodified on both sides of the web stack (the server, under CPython,
and the client, under Brython).

An :class:`Effect` is used as a context manager: the code of the block
runs inside the effect's scope, and a signal read in the scope (a
getter child of a component — see :mod:`kopis.common.component`)
registers the read as an observer of the signal::

    signal = Signal(0)
    get_count, set_count = signal

    with Effect():          # k.effect() is the app's way to make one
        with k.document.body:
            Button(get_count)  # the button's text follows the signal

When the signal changes (``set_count(new_value)``), the observer runs,
re-reads the value, and re-renders it in place. As a solidjs effect
keeps observing until it is disposed, the effect keeps observing for
the lifetime of the app when the block ends; :meth:`Effect.dispose`
stops it early.
"""

from collections.abc import Callable
from typing import Any, Self

from .signal import Signal, _scopes

__all__ = ["Effect"]


class Effect:
    """A reactive scope, in the spirit of solidjs's ``createEffect``
    (the ``with k.effect():`` block form of it).

    The code of the ``with`` block runs inside the effect's scope: a
    signal read in the scope (a getter child of a component, see
    :mod:`kopis.common.component`) registers the read as an observer
    of the signal. When the signal changes, the observer re-reads the
    value and re-renders it in place. The effect keeps observing for
    the lifetime of the app, as a solidjs effect keeps observing until
    it is disposed; :meth:`dispose` stops it early.
    """

    #: This effect's observations, as ``(signal, callback)`` pairs (the
    #: ones it removes on :meth:`dispose`).
    subscriptions: list[tuple[Signal, Callable[[], Any]]]

    #: The update callback of the read :meth:`track` is currently
    #: tracking, else ``None``.
    tracking: Callable[[], Any] | None

    def __init__(self) -> None:
        self.subscriptions = []
        self.tracking = None

    def __enter__(self) -> Self:
        """Enter the effect's scope: the signal reads of the block run
        in it (and are tracked)."""
        _scopes.append(self)
        return self

    def __exit__(self, *exc_info: object) -> bool:
        """Leave the scope. The effect keeps observing (its
        observations are removed only by :meth:`dispose`), as a solidjs
        effect keeps observing until it is disposed. Exceptions are not
        suppressed."""
        if _scopes and _scopes[-1] is self:
            _scopes.pop()
        return False

    def track(self, child: Callable[[], Any], update: Callable[[], Any]) -> Any:
        """Call ``child`` with ``update`` as the callback of the read:
        each signal read during the call registers ``update`` as an
        observer of the signal (so a change of the signal re-runs
        ``update``, which re-reads and re-renders the value).

        Returns what ``child`` returned (a value, or a coroutine).
        """
        previous = self.tracking
        self.tracking = update
        try:
            return child()
        finally:
            self.tracking = previous

    def observe(self, signal: Signal, update: Callable[[], Any]) -> None:
        """Register ``update`` as an observer of ``signal`` (the solidjs
        way the effect observes the signals it reads): a no-op if
        ``update`` is already registered with ``signal``."""
        pair = (signal, update)
        if pair not in self.subscriptions:
            self.subscriptions.append(pair)
            signal._observe(update)

    def dispose(self) -> None:
        """Stop the effect's observations (the solidjs dispose): the
        signals it reads are no longer updated by it."""
        if _scopes and _scopes[-1] is self:
            _scopes.pop()
        for signal, update in self.subscriptions:
            signal._forget(update)
        self.subscriptions.clear()

    def __repr__(self) -> str:
        return f"<Effect {len(self.subscriptions)} observation(s)>"
