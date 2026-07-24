# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""An `AwaitableDialog` that can be used in `prompt_toolkit."""

from asyncio import Future, get_running_loop
from typing import TYPE_CHECKING, Any, final, override

from prompt_toolkit.widgets import Button, Dialog

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence


@final
class AwaitableDialog[T: str](Dialog):
    """A dialog you can `await` (resolves when the 'ok' button is pressed)."""

    _future: Future[T | None]

    @override
    def __init__(self, buttons: Sequence[Button] | None = None, **kwargs: Any) -> None:
        self._future = get_running_loop().create_future()

        dialog_buttons: list[Button] = list(buttons or [])
        dialog_buttons.append(Button(text='Ok', handler=lambda: self.finish(None)))

        super().__init__(buttons=dialog_buttons, **kwargs)

    def finish(self, result: T | None) -> None:
        """Resolve the dialog's `Future`."""
        if not self._future.done():
            self._future.set_result(result)

    def __await__(self) -> Generator[Any, None, T | None]:
        """Lets you just `await dialog` instead of `await dialog.future`.

        Returns:
            The value set by the `finish()` method

        """
        return self._future.__await__()
