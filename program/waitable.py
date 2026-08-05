# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Make something "awaitable" using `anyio.Event` instead of `asyncio.Future`."""

from typing import TYPE_CHECKING, Any

from anyio import Event

if TYPE_CHECKING:
    from collections.abc import Generator


class Waitable[T]:
    """Makes any class "awaitable", just call `finish()`."""

    _event: Event
    _result: T | None = None

    def _init_waitable(self) -> None:
        self._event = Event()

    def finish(self, result: T | None) -> None:
        """Mark the Event as set (the equivalent of `future.set_result`)."""
        if not self._event.is_set():
            self._result = result
            self._event.set()

    async def wait(self) -> T | None:
        """Wait for the Event and return the result (the equivalent of `await future`).

        Returns:
            The value set in the `finish()` method

        """
        await self._event.wait()
        return self._result

    def __await__(self) -> Generator[Any, None, T | None]:
        """Lets you just `await obj` instead of `await future`.

        Returns:
            The value set by the `finish()` method

        """
        return self.wait().__await__()
