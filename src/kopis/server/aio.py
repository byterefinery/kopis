"""Async I/O for the server side.

A thin facade over :mod:`asyncio` mirroring the surface of
``browser.aio`` used by client-side code, so the same application code
runs unmodified on both sides.
"""

import asyncio
from collections.abc import Coroutine

__all__ = ["Future", "run", "sleep"]


def run(coro: Coroutine) -> None:
    """Start a coroutine without blocking (the brython ``aio.run``,
    which returns ``None``, so this one does too)."""
    asyncio.ensure_future(coro)


async def sleep(delay: float) -> None:
    """Suspend execution for ``delay`` seconds (the brython
    ``aio.sleep``)."""
    await asyncio.sleep(delay)


def Future() -> asyncio.Future:
    """A future of a pending asynchronous call (the brython
    ``aio.Future``). Requires a running event loop."""
    return asyncio.get_running_loop().create_future()
