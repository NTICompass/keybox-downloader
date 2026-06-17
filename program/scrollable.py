from asyncio import Task
from collections.abc import Callable
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseEventType, MouseEvent
from typing import final, override


@final
class ScrollableTextControl(FormattedTextControl):
    def __init__(
        self,
        *args,
        on_scroll: Callable[[int], None | Task[None]] = lambda _: None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.__on_scroll = on_scroll

    @override
    def mouse_handler(self, mouse_event: MouseEvent):
        delta = {
            MouseEventType.SCROLL_UP: -1,
            MouseEventType.SCROLL_DOWN: 1,
        }.get(mouse_event.event_type)

        if delta is not None:
            self.__on_scroll(delta)
            return None

        # Let FormattedTextControl dispatch clicks to fragment handlers.
        return super().mouse_handler(mouse_event)
