# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""An `ScrollableTextControl` that can be used in `prompt_toolkit."""

from typing import TYPE_CHECKING, Any, final, override

from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType

if TYPE_CHECKING:
    from collections.abc import Callable

    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone


@final
class ScrollableTextControl(FormattedTextControl):
    """A `FormattedTextControl` but you can scroll up and down."""

    @override
    def __init__(self, on_scroll: Callable[[int], None] = lambda _: None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__on_scroll = on_scroll

    @override
    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Add the ability to scroll up and down to the panel.

        Args:
            mouse_event: The `MouseEvent`

        Returns:
            `NotImplemented` ot `None`

        """
        delta = {MouseEventType.SCROLL_UP: -1, MouseEventType.SCROLL_DOWN: 1}.get(mouse_event.event_type)

        if delta is not None:
            self.__on_scroll(delta)
            return None

        # Let FormattedTextControl dispatch clicks to fragment handlers.
        return super().mouse_handler(mouse_event)
