"""Async I/O for the server side.

A thin facade over :mod:`asyncio` mirroring the surface of
``browser.aio`` used by client-side code, so the same application code
runs unmodified on both sides.
"""

__all__ = ["run", "sleep"]

import asyncio
from collections.abc import Coroutine


def run(coro: Coroutine) -> asyncio.Task:
    """Start a coroutine without blocking, returning the task that wraps it."""
    return asyncio.ensure_future(coro)


async def sleep(delay: float) -> None:
    """Suspend execution for ``delay`` seconds."""
    await asyncio.sleep(delay)
