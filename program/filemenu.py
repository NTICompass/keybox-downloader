# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""The main program/file picker."""

from collections.abc import AsyncIterable, Awaitable, Callable, Generator, Iterable
from functools import partial
from itertools import groupby
from typing import TYPE_CHECKING, ClassVar, Literal, final

import anyio
import anyio.lowlevel
from anyio import Path
from prompt_toolkit.application import Application
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import ConditionalKeyBindings, KeyBindings, KeyPressEvent, merge_key_bindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import ConditionalContainer, Float, FloatContainer, HSplit, Layout, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Box, Button, Dialog, Frame, ProgressBar

import __main__
from cache_data import Overrides
from downloaders import Downloader

from . import Action
from .android import Android
from .dialog import AwaitableDialog
from .helpers import gather
from .keybox import Keybox
from .options import Options
from .scrollable import ScrollableTextControl

if TYPE_CHECKING:
    from prompt_toolkit.formatted_text import StyleAndTextTuples

type EventFunc = Callable[[], Awaitable[None] | None]
root: Path = __main__.root
folder: Path = __main__.exe_root / 'keyboxes'


@final
class FileMenu:
    """Launcher for the file-browser, can download new keyboxes or install them on a phone."""

    android: ClassVar[Android] = Android()
    overrides: ClassVar[Overrides[type[Downloader]]] = Overrides()

    action: Action
    app: Application[Path | None]
    device_info_text = ''
    dialog_shown: Literal[False, 'options', 'download', 'progress'] = False
    dl_dialog: AwaitableDialog[Literal['force']]
    files: dict[str, Keybox]
    ignore_empty: bool
    keybox_info_text: StyleAndTextTuples
    keyboxes: list[Path]
    menu_control: Window
    opts: Options
    root_float: FloatContainer
    selectable_rows: list[int]
    selected_index = 0

    def __init__(self, *, ignore_empty: bool = False) -> None:
        """Set the options for the file-browser.

        Args:
            ignore_empty: `True` to allow empty file list, `False` to quit on empty file list

        """
        self.ignore_empty = ignore_empty
        self.files = {}
        self.selectable_rows = []
        self.keybox_info_text = []
        self.action = Action()

    async def _init_app(self, keybox_iter: Iterable[Path] | AsyncIterable[Path]) -> None:
        """Run `prompt_toolkit` and show the file-picker menu.  Return the selected file.

        Args:
            keybox_iter: (Async) Iterable of keyboxes to display in the file browser

        """
        if isinstance(keybox_iter, AsyncIterable):
            self.keyboxes = [keybox_file async for keybox_file in keybox_iter]
        else:
            self.keyboxes = list(keybox_iter)

        if not self.ignore_empty and len(self.keyboxes) == 0:
            print('No valid keyboxes found')
            return

        await Keybox.init_attestation(Downloader.client)
        self.keyboxes.sort(
            key=lambda file: (file.parent.name, self._get_cert_serials(file, certs_only=True)[0], file.name)
        )

        kb, dl_kb = (KeyBindings(), KeyBindings())

        # Start the app and preload the panels with information
        if len(self.keyboxes) > 0:
            self._keybox_info(do_invalidate=False)

        await self._refresh_device(do_invalidate=False)

        self.menu_control = Window(
            ScrollableTextControl(
                text=self._file_list,
                focusable=True,
                get_cursor_position=lambda: Point(
                    0, self.selectable_rows[self.selected_index] if len(self.selectable_rows) > 0 else 0
                ),
                on_scroll=self._move,
            )
        )
        preview = Window(FormattedTextControl(text=lambda: self.keybox_info_text, focusable=False))

        # The warning here is due to https://youtrack.jetbrains.com/issue/PY-89873
        @Condition
        def keybox_filter() -> bool:
            return len(self.keyboxes) > 0

        @Condition
        def device_attached() -> bool:
            return Android.is_android or self.android.device is not None

        continue_button = ConditionalContainer(
            Button(text='Continue', handler=lambda: self.app.exit(result=self.keyboxes[self.selected_index])),
            device_attached,
            Button(text='No Device Found'),
        )

        device_info = Window(FormattedTextControl(text=lambda: self.device_info_text))

        # Keyboard events
        @kb.add(Keys.Up, filter=keybox_filter)
        def _(event: KeyPressEvent) -> None:  # ruff: ignore[unused-function-argument]
            self._move(-1)

        @kb.add(Keys.Down, filter=keybox_filter)
        def _(event: KeyPressEvent) -> None:  # ruff: ignore[unused-function-argument]
            self._move(1)

        @kb.add(Keys.Enter, filter=device_attached)
        def _(event: KeyPressEvent) -> None:
            if len(self.keyboxes) > 0:
                event.app.exit(result=self.keyboxes[self.selected_index])

        @kb.add('d')
        async def _(event: KeyPressEvent) -> None:  # ruff: ignore[unused-function-argument]
            await self._do_download()

        @kb.add('o')
        async def _(event: KeyPressEvent) -> None:  # ruff: ignore[unused-function-argument]
            await self._open_options()

        @kb.add(Keys.F5)
        @kb.add('r')
        async def _(event: KeyPressEvent) -> None:
            await event.app.create_background_task(self._refresh_device())

        @kb.add('q')
        def _(event: KeyPressEvent) -> None:
            event.app.exit(result=None)

        @dl_kb.add('f')
        def _(event: KeyPressEvent) -> None:  # ruff: ignore[unused-function-argument]
            self.dl_dialog.finish('force')

        def status_handler(func: EventFunc) -> Callable[[MouseEvent], Awaitable[None]]:
            async def click(mouse_event: MouseEvent) -> None:
                if (
                    mouse_event.button == MouseButton.LEFT
                    and mouse_event.event_type == MouseEventType.MOUSE_UP
                    and self.dialog_shown != 'progress'
                ):
                    result = func()

                    if result is not None:
                        await result

            return click

        status_keys: dict[Literal['d', 'r', 'o', 'q'], tuple[str, EventFunc]] = {
            'd': ('Run downloaders', self._do_download),
            'r': ('Reload / Re-scan devices', lambda: self.app.create_background_task(self._refresh_device())),
            'o': ('Options', self._open_options),
            'q': ('Quit', lambda: self.app.exit(result=None)),
        }

        status_bar = Window(
            content=FormattedTextControl(
                [
                    item
                    for key, (text, func) in status_keys.items()
                    for item in (
                        ('class:key', f'[{key.upper()}] ', status_handler(func)),
                        ('', f'{text.title()} ', status_handler(func)),
                    )
                ]
            ),
            height=2 if Android.is_android else 1,
            style='class:toolbar',
        )

        if Android.is_android:
            root_win = HSplit(
                [
                    VSplit(
                        [Frame(self.menu_control, title='Available Keyboxes'), Frame(device_info, title='Device Info')],
                        width=Dimension(weight=1),
                    ),
                    Frame(preview, title='Keybox Info', width=Dimension(weight=1)),
                    status_bar,
                ]
            )
        else:
            root_win = HSplit(
                [
                    VSplit(
                        [
                            HSplit(
                                [
                                    Frame(self.menu_control, title='Available Keyboxes'),
                                    Frame(device_info, title='Device Info'),
                                ],
                                width=Dimension(weight=1),
                            ),
                            Frame(preview, title='Keybox Info', width=Dimension(weight=2)),
                        ]
                    ),
                    continue_button,
                    status_bar,
                ]
            )

        self.root_float = FloatContainer(content=root_win, floats=[])
        self.app = Application[Path | None](
            layout=Layout(self.root_float, focused_element=self.menu_control),
            full_screen=True,
            key_bindings=merge_key_bindings(
                [
                    ConditionalKeyBindings(kb, filter=Condition(lambda: not self.dialog_shown)),
                    ConditionalKeyBindings(dl_kb, filter=Condition(lambda: self.dialog_shown == 'download')),
                ]
            ),
            mouse_support=Condition(lambda: not Android.is_android),
            style=Style.from_dict(
                {
                    'checkbox': 'fg:black',
                    'checkbox-checked': 'fg:red bold',
                    'checkbox-selected': 'reverse bold',
                    'toolbar': 'reverse',
                    'key': 'bold',
                    'validity': 'bold',
                    'valid': 'fg:green',
                    'revoked': 'fg:red',
                    'semi_valid': 'fg:blue',
                    'aosp': 'fg:purple',
                }
            ),
        )

        if not Android.is_android:
            self.app.output.show_cursor = lambda: None

        if self.app.layout:
            self.app.layout.focus(self.menu_control)

    async def _get_device(self) -> str:
        """Show device info in the side-panel.

        Returns:
            Device information - manufacturer and fingerprint (if connected).

        """
        if Android.is_android:
            return await self.android.get_prop('ro.system.build.fingerprint')

        manufacturer, fingerprint = await gather(
            self.android.get_prop('ro.product.manufacturer'), self.android.get_prop('ro.system.build.fingerprint')
        )
        props = '\n'.join(
            [
                await self.android.get_prop('ro.vendor.asus.product.mkt_name')
                if manufacturer == 'asus'
                else await self.android.get_prop(),
                fingerprint,
            ]
        )

        return props if props.strip() else 'No device found, press "r" to re-try'

    async def _refresh_device(self, *, do_invalidate: bool = True) -> None:
        """Reload the device info side-panel (like, when a phone is connected).

        Args:
            do_invalidate: `True` to call `app.invalidate()`

        """
        self.android.reset_device()
        self.device_info_text = await self._get_device()

        if do_invalidate:
            self.app.invalidate()

    def _get_cert_serials(self, file: Path, *, certs_only: bool = False) -> list[str]:
        """Get the serial numbers for the keybox file.

        Args:
            file: The keybox file
            certs_only: `True` to skip the validity check

        Returns:
            A list of certificate serials in the keybox

        """
        if file.name not in self.files:
            self.files[file.name] = Keybox(file)

        all_certs = [
            cert if certs_only else f'{cert} ({"Valid" if valid else "Revoked"})'
            for cert, valid in self.files[file.name].keys_valid.items()
        ]
        ec_certs, rsa_certs = self.files[file.name].key_counts

        return all_certs if certs_only else [f'{ec_certs} EC certs, {rsa_certs} RSA certs', *all_certs]

    def _keybox_info(self, *, do_invalidate: bool = True) -> None:
        """Show serials/validity for selected keybox in side-panel.

        Args:
            do_invalidate: `True` to call `app.invalidate()`

        """
        self.keybox_info_text = (
            [
                (
                    f'class:validity class:{self.keyboxes[self.selected_index].parent.name}',
                    self.keyboxes[self.selected_index].parent.name,
                ),
                (
                    '',
                    (
                        f' / {self.keyboxes[self.selected_index].name}: '
                        f'{"\n".join(self._get_cert_serials(self.keyboxes[self.selected_index]))}'
                    ),
                ),
            ]
            if len(self.keyboxes) > 0
            else []
        )

        if do_invalidate:
            self.app.invalidate()

    def _file_list(self) -> StyleAndTextTuples:
        """Show the list of keybox files in the main panel.

        Returns:
            List of keybox file rows

        """

        def click(idx: int, mouse_event: MouseEvent) -> None:
            """Click on a file, to select it and show its info in the side-panel.

            Args:
                idx: Which file did you click on?
                mouse_event: `MouseEvent` - used to get which mouse button was pressed

            """
            if mouse_event.button == MouseButton.LEFT and mouse_event.event_type == MouseEventType.MOUSE_UP:
                self.selected_index = idx
                self._keybox_info(do_invalidate=False)

        rows: StyleAndTextTuples = []
        start = 0
        cursor = 0

        for kb_folder, kb_files in groupby(self.keyboxes, key=lambda file: file.parent.name):
            rows.append((f'class:{kb_folder}', f'{kb_folder}\n'))
            cursor += 1

            for kb_idx, kb_file in enumerate(kb_files, start=start):
                rows.append(
                    (
                        'class:selected' if kb_idx == self.selected_index else '',
                        f'{"->" if kb_idx == self.selected_index else "  "} {kb_folder} / {kb_file.name}\n',
                        partial(click, kb_idx),
                    )
                )
                self.selectable_rows.append(cursor)

                start += 1
                cursor += 1

        return rows

    def _move(self, delta: int) -> None:
        """Move the `selected_index` (on the file-browser) up and down.

        Args:
            delta: How many positions (files) to move (positive for down, negative for up)

        """
        self.selected_index = (self.selected_index + delta) % len(self.keyboxes)
        self._keybox_info(do_invalidate=False)

    async def _do_download(self) -> None:
        """Run the `Download` modules from `action.py` and show progress in a dialog."""

        async def run() -> None:
            self.dialog_shown = 'progress'
            progress_bar = ProgressBar()
            completed: list[str] = []

            async def update_progress(current: int, total: int, dl_complete: str) -> None:
                progress_bar.percentage = (current * 100) // total
                completed.append(dl_complete)

                # Both lines below are needed to actually draw the progress bar updates
                self.app.invalidate()

                # https://docs.astral.sh/ruff/rules/async-zero-sleep/
                await anyio.lowlevel.checkpoint()

            self.root_float.floats.append(
                Float(
                    content=Dialog(
                        title='Downloading...',
                        body=HSplit(
                            [
                                Box(progress_bar, width=30, padding_right=2, padding_left=2),
                                Frame(Window(FormattedTextControl(text=lambda: '\n'.join(completed))), 'Completed'),
                            ]
                        ),
                    )
                )
            )

            progress_bar.percentage = 0
            self.app.invalidate()
            await self.action(*Action.get_downloaders(), progress=update_progress)
            await anyio.sleep(1)

            self.root_float.floats.pop()

            self.keyboxes = [keybox_file async for keybox_file in folder.rglob('*.xml')]
            self._keybox_info(do_invalidate=True)
            self.dialog_shown = False

        if self.action.can_run():
            await self.app.create_background_task(run())
        else:
            self.dialog_shown = 'download'

            self.dl_dialog = AwaitableDialog[Literal['force']](
                title='Notice',
                body=Window(FormattedTextControl(text='Downloaders can only be ran once every 24hrs')),
            )

            self.root_float.floats.append(Float(content=self.dl_dialog))
            if self.app.layout:
                self.app.layout.focus(self.dl_dialog)
            self.app.invalidate()

            result = await self.dl_dialog
            self.dialog_shown = False
            self.root_float.floats.pop()

            if self.app.layout:
                self.app.layout.focus(self.menu_control)
            self.app.invalidate()

            if result == 'force':
                self.action.force_run()
                await self.app.create_background_task(run())

    async def _open_options(self) -> None:
        """Open the options dialog to set which `Downloader` modules are enabled."""
        self.dialog_shown = 'options'

        opts = Options(is_android=Android.is_android)
        self.root_float.floats.append(Float(content=opts.dialog))

        if self.app.layout:
            self.app.layout.focus(opts.dialog)
        self.app.invalidate()

        enabled = await opts

        if enabled is not None:
            dl_selected = set(enabled)
            all_downloaders: set[type[Downloader]] = Downloader.enabled | Downloader.disabled

            Downloader.enabled.clear()
            Downloader.disabled.clear()

            Downloader.enabled.update(dl_selected)
            Downloader.disabled.update(all_downloaders - dl_selected)

            for dl in all_downloaders:
                self.overrides.toggle(dl, value=dl in dl_selected)
            self.overrides.save()

        self.root_float.floats.pop()

        if self.app.layout:
            self.app.layout.focus(self.menu_control)
        self.app.invalidate()

        self.dialog_shown = False

    async def __launch(self) -> None:
        """Start the `prompt_toolkit` app and wait for it to complete."""
        await self._init_app(folder.rglob('*.xml'))
        selected_file = await self.app.run_async()

        if selected_file is None:
            print('Exiting')
        else:
            print(f'Installing {selected_file}')
            await self.android.install(folder / selected_file)

    def __await__(self) -> Generator:
        """Use `await fileMenu` to run the app.

        Returns:
            `None`

        """
        return self.__launch().__await__()
