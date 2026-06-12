from asyncio import get_running_loop, Future
from downloaders import Downloader
from importlib.metadata import version
from operator import itemgetter
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout.containers import VSplit, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import CheckboxList, Dialog, Button, Frame, Box
from typing import ClassVar


class CheckboxSelected[T](CheckboxList[T]):
    @property
    def current_item(self) -> T:
        return self.values[self._selected_index][0]


class Options:
    APP_VERSION: ClassVar[str] = version('keybox-downloader')

    future: Future[list[type[Downloader]] | None]
    dialog: Dialog
    __checkboxes: CheckboxSelected[type[Downloader]]

    def __init__(self, is_android: bool):
        self.future = get_running_loop().create_future()
        kb = KeyBindings()

        self.__checkboxes = CheckboxSelected[type[Downloader]](
            values=sorted(
                [(dl, dl.__name__) for dl in Downloader.enabled | Downloader.disabled],
                key=itemgetter(1),
            ),
            default_values=tuple(Downloader.enabled),
        )
        self.__checkboxes.show_scrollbar = False

        desc_window = Window(
            content=FormattedTextControl(
                text=lambda: self.__checkboxes.current_item.DESCRIPTION
            ),
            wrap_lines=True,
        )

        if is_android:
            body = [
                Window(content=FormattedTextControl(text='Select downloaders:')),
                Box(body=self.__checkboxes, width=35),
                Frame(body=desc_window, title='Description', width=50),
            ]
        else:
            body = [
                Window(content=FormattedTextControl(text='Select downloaders:')),
                VSplit(
                    [
                        Box(body=self.__checkboxes, width=35),
                        Frame(body=desc_window, title='Description', width=75),
                    ],
                    padding=1,
                ),
            ]

        @kb.add('s')
        def _(event: KeyPressEvent):
            self.__save()

        @kb.add('c')
        @kb.add('q')
        def _(event: KeyPressEvent):
            self.__cancel()

        self.dialog = Dialog(
            title=f'Keybox Downloader v{self.APP_VERSION}',
            body=HSplit(children=body, key_bindings=kb),
            buttons=[
                Button(text='Save', handler=self.__save),
                Button(text='Cancel', handler=self.__cancel),
            ],
        )

    def __save(self):
        self.future.set_result(self.__checkboxes.current_values)

    def __cancel(self):
        self.future.set_result(None)
