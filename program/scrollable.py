from collections.abc import Callable
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseEventType, MouseEvent
from typing import Awaitable, override, final


@final
class ScrollableTextControl(FormattedTextControl):
    def __init__(
        self,
        *args,
        on_scroll: Callable[[int], None | Awaitable[None]] = lambda x: None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.__on_scroll = on_scroll

    @override
    def mouse_handler(self, mouse_event: MouseEvent):
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            self.__on_scroll(-1)
            return None
        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self.__on_scroll(1)
            return None

        # Let FormattedTextControl dispatch clicks to fragment handlers.
        return super().mouse_handler(mouse_event)
