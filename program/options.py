from asyncio import get_running_loop, Future
from downloaders import Downloader
from importlib.metadata import version
from operator import itemgetter
from prompt_toolkit.widgets import CheckboxList, Dialog, Button
from typing import ClassVar


class Options:
    APP_VERSION: ClassVar[str] = version('keybox-downloader')

    def __init__(self):
        self.future: Future[list[type[Downloader]] | None] = (
            get_running_loop().create_future()
        )

        checkboxes = CheckboxList(
            values=sorted(
                [(dl, dl.__name__) for dl in Downloader.enabled | Downloader.disabled],
                key=itemgetter(1),
            ),
            default_values=tuple(Downloader.enabled),
        )

        self.dialog = Dialog(
            title=f'Keybox Downloader v{self.APP_VERSION}',
            body=checkboxes,
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
