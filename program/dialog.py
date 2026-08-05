# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""An `AwaitableDialog` that can be used in `prompt_toolkit."""

from typing import TYPE_CHECKING, Any, final, override

import anyio
from prompt_toolkit.widgets import Button, Dialog

from .waitable import Waitable

if TYPE_CHECKING:
    from collections.abc import Sequence


@final
class AwaitableDialog[T: str](Waitable[T], Dialog):
    """A dialog you can `await` (resolves when the 'ok' button is pressed)."""

    @override
    def __init__(self, buttons: Sequence[Button] | None = None, **kwargs: Any) -> None:
        dialog_buttons: list[Button] = list(buttons or [])
        dialog_buttons.append(Button(text='Ok', handler=lambda: self.finish(None)))

        super().__init__(buttons=dialog_buttons, **kwargs)
        self._init_waitable()
