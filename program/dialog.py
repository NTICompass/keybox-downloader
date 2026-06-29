from asyncio import Future, get_running_loop
from collections.abc import Sequence, Generator
from prompt_toolkit.widgets import Dialog, Button
from typing import final, override, Any


@final
class AwaitableDialog[T: str](Dialog):
    _future: Future[T | None]

    @override
    def __init__(self, buttons: Sequence[Button] | None = None, **kwargs):
        self._future = get_running_loop().create_future()

        dialog_buttons: list[Button] = list(buttons or [])
        dialog_buttons.append(Button(text='Ok', handler=lambda: self.finish(None)))

        super().__init__(buttons=dialog_buttons, **kwargs)

    def finish(self, result: T | None) -> None:
        if not self._future.done():
            self._future.set_result(result)

    def __await__(self) -> Generator[Any, None, T | None]:
        return self._future.__await__()
