# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Helpers for `asyncio.gather()` and `asyncio.as_completed()` using `anyio`."""

from collections.abc import Awaitable
from typing import TYPE_CHECKING

import anyio

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, Iterable


async def gather[T](*tasks: Awaitable[T]) -> list[T]:
    """Run multiple coroutines in a TaskGroup and return their results in order.

    Args:
        tasks: Anything awaitable (Task, Coroutine, etc.)

    Returns:
        The results in the order they were passed in

    """
    results: list[T] = [None] * len(tasks)

    async def run(result_idx: int, coro: Awaitable[T]) -> None:
        results[result_idx] = await coro

    async with anyio.create_task_group() as tg:
        for idx, task in enumerate(tasks):
            tg.start_soon(run, idx, task)

    return results


async def as_completed[T](tasks: Iterable[Awaitable[T]]) -> AsyncIterable[Awaitable[T]]:
    """Run multiple coroutines in a TaskGroup and return their results in as they complete.

    Args:
        tasks: Collection of anything awaitable (Task, Coroutine, etc.)

    Yields:
        The results in the order they completed (you need to `await` the result)

    """
    send, receive = anyio.create_memory_object_stream[Awaitable[T]]()

    async def run(coro: Awaitable[T]) -> None:
        result = await coro

        async def done(value: T = result) -> T:  # ruff: ignore[unused-async]
            return value

        await send.send(done())

    async with send, receive, anyio.create_task_group() as tg:
        n = 0
        for task in tasks:
            tg.start_soon(run, task)
            n += 1

        for _ in range(n):
            yield await receive.receive()  # ruff: ignore[yield-in-context-manager-in-async-generator]
