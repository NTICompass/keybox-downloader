from asyncio import get_running_loop, Future
from downloaders import Downloader
from importlib.metadata import version
from operator import itemgetter
from prompt_toolkit.layout.containers import VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import CheckboxList, Dialog, Button, Frame
from typing import ClassVar


class CheckboxSelected[T](CheckboxList):
    @property
    def current_item(self) -> T:
        return self.values[self._selected_index][0]


class Options:
    APP_VERSION: ClassVar[str] = version('keybox-downloader')

    def __init__(self):
        self.future: Future[list[type[Downloader]] | None] = (
            get_running_loop().create_future()
        )

        checkboxes = CheckboxSelected[type[Downloader]](
            values=sorted(
                [(dl, dl.__name__) for dl in Downloader.enabled | Downloader.disabled],
                key=itemgetter(1),
            ),
            default_values=tuple(Downloader.enabled),
        )

        desc_window = Window(
            content=FormattedTextControl(
                text=lambda: checkboxes.current_item.DESCRIPTION
            ),
            wrap_lines=True,
        )

        self.dialog = Dialog(
            title=f'Keybox Downloader v{self.APP_VERSION}',
            body=VSplit(
                [
                    checkboxes,
                    Frame(desc_window, title='Description'),
                ],
                padding=1,
            ),
            buttons=[
                Button(
                    text='Save',
                    handler=lambda: self.future.set_result(checkboxes.current_values),
                ),
                Button(
                    text='Cancel',
                    handler=lambda: self.future.set_result(None),
                ),
            ],
        )
