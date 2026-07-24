# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""The main `prompt_toolkit` menu and the keybox installer."""

import asyncio
import sys
from collections.abc import AsyncIterable, Awaitable, Callable, Iterable
from contextlib import suppress
from functools import partial
from itertools import groupby
from typing import TYPE_CHECKING, Literal

from anyio import Path
from prompt_toolkit.application import Application, get_app
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
from program.keybox import Keybox

from .action import can_run, force_run, get_downloaders, go
from .dialog import AwaitableDialog
from .options import Options
from .scrollable import ScrollableTextControl

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from prompt_toolkit.formatted_text import StyleAndTextTuples

is_android = hasattr(sys, 'getandroidapilevel')

try:
    from adbutils import AdbError, adb

    if TYPE_CHECKING:
        from adbutils import AdbDevice

    device: AdbDevice | None
except ImportError as err:
    if is_android:
        from subprocess import CalledProcessError

        from anyio import run_process
    else:
        msg = 'adbutils is required on PC'
        raise RuntimeError(msg) from err
finally:
    device = None

root: Path = __main__.root
folder: Path = __main__.exe_root / 'keyboxes'
tmp_folder = '/data/local/tmp'
key_file = f'{tmp_folder}/my_keybox.xml'
runner = {'pc': 'install_keybox.sh', 'android': 'install_android.sh'}

current_keybox: Keybox | None = None
files: dict[str, Keybox] = {}
overrides: Overrides[type[Downloader]] = Overrides()

type EventFunc = (
    Callable[[Application[Path | None]], None]
    | Callable[[], None]
    | Callable[[Application[Path | None]], Awaitable[None]]
    | Callable[[], Awaitable[None]]
)


async def get_prop(prop: str | None = None) -> str:
    """Get a property value from the currently connected Android phone (or the phone we're running on).

    Args:
        prop: The property name, like "ro.system.build.fingerprint"

    Returns:
        The property value

    """
    global device

    if is_android and prop is not None:
        with suppress(CalledProcessError):
            proc = await run_process(['/system/bin/getprop', prop], check=True)
            return proc.stdout.decode().strip()
    if not is_android and adb is not None:
        with suppress(AdbError):
            if device is None:
                # Connect to the 1st device (throws exception if there are zero or multiple)
                device = adb.device()

            if device is not None:
                return str(device.getprop(prop) if prop is not None else device.prop).strip()
    return ''


async def get_device() -> str:
    """Show device info in the side-panel.

    Returns:
        Device information - manufacturer and fingerprint (if connected).

    """
    if is_android:
        return await get_prop('ro.system.build.fingerprint')

    manufacturer, fingerprint = await asyncio.gather(
        get_prop('ro.product.manufacturer'), get_prop('ro.system.build.fingerprint')
    )
    props = '\n'.join(
        [await get_prop('ro.vendor.asus.product.mkt_name') if manufacturer == 'asus' else await get_prop(), fingerprint]
    )

    return props if props.strip() else 'No device found, press "r" to re-try'


def get_cert_serials(file: Path, *, certs_only: bool = False) -> list[str]:
    """Get the serial numbers for the keybox file.

    Args:
        file: The keybox file
        certs_only: `True` to skip the validity check

    Returns:
        A list of certificate serials in the keybox

    """
    if file.name not in files:
        files[file.name] = Keybox(file)

    all_certs = [
        cert if certs_only else f'{cert} ({"Valid" if valid else "Revoked"})'
        for cert, valid in files[file.name].keys_valid.items()
    ]
    ec_certs, rsa_certs = files[file.name].key_counts

    return all_certs if certs_only else [f'{ec_certs} EC certs, {rsa_certs} RSA certs', *all_certs]


async def select_file(keybox_iter: Iterable[Path] | AsyncIterable[Path], *, ignore_empty: bool = False) -> Path | None:
    """Run `prompt_toolkit` and show the file-picker menu.  Return the selected file.

    Args:
        keybox_iter: (Async) Iterable of keyboxes to display in the file browser
        ignore_empty: `True` to allow empty file list, `False` to error out on empty file list

    Returns:
        The selected keybox file (or `None` if "quit" was pressed)

    """
    if isinstance(keybox_iter, AsyncIterable):
        keyboxes = [keybox_file async for keybox_file in keybox_iter]
    else:
        keyboxes = list(keybox_iter)

    if not ignore_empty and len(keyboxes) == 0:
        print('No valid keyboxes found')
        return None

    await Keybox.init_attestation(Downloader.client)
    keyboxes.sort(key=lambda file: (file.parent.name, get_cert_serials(file, certs_only=True)[0], file.name))

    selected_index = 0
    selectable_rows: list[int] = []
    device_info_text = ''
    keybox_info_text: StyleAndTextTuples = []
    dialog_shown: Literal[False, 'options', 'download', 'progress'] = False
    dl_dialog: AwaitableDialog[Literal['force']]

    app: Application[Path | None] = get_app()
    kb = KeyBindings()
    dl_kb = KeyBindings()
    opts: Options
    menu_control: Window
    root_float: FloatContainer

    async def refresh_device(evt_app: Application[Path | None] | None = None) -> None:
        """Reload the device info side-panel (like, when a phone is connected).

        Args:
            evt_app: The running `Application` (`None` to get automatically)

        """
        nonlocal device_info_text

        device_info_text = await get_device()
        (evt_app if evt_app is not None else app).invalidate()

    def keybox_info(*, do_invalidate: bool = True) -> None:
        """Show serials/validity for selected keybox in side-panel.

        Args:
            do_invalidate: `True` to call `app.invalidate()`

        """
        nonlocal keybox_info_text

        keybox_info_text = (
            [
                (f'class:validity class:{keyboxes[selected_index].parent.name}', keyboxes[selected_index].parent.name),
                ('', f' / {keyboxes[selected_index].name}: {"\n".join(get_cert_serials(keyboxes[selected_index]))}'),
            ]
            if len(keyboxes) > 0
            else []
        )

        if do_invalidate:
            app.invalidate()

    def file_list() -> StyleAndTextTuples:
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
            nonlocal selected_index

            if mouse_event.button == MouseButton.LEFT and mouse_event.event_type == MouseEventType.MOUSE_UP:
                selected_index = idx
                keybox_info(do_invalidate=False)

        rows: StyleAndTextTuples = []
        start = 0
        cursor = 0

        for kb_folder, kb_files in groupby(keyboxes, key=lambda file: file.parent.name):
            rows.append((f'class:{kb_folder}', f'{kb_folder}\n'))
            cursor += 1

            for kb_idx, kb_file in enumerate(kb_files, start=start):
                rows.append(
                    (
                        'class:selected' if kb_idx == selected_index else '',
                        f'{"->" if kb_idx == selected_index else "  "} {kb_folder} / {kb_file.name}\n',
                        partial(click, kb_idx),
                    )
                )
                selectable_rows.append(cursor)

                start += 1
                cursor += 1

        return rows

    def move(delta: int) -> None:
        """Move the `selected_index` (on the file-browser) up and down.

        Args:
            delta: How many positions (files) to move (positive for down, negative for up)

        """
        nonlocal selected_index

        selected_index = (selected_index + delta) % len(keyboxes)
        keybox_info(do_invalidate=False)

    # Start the app and preload the panels with information
    if len(keyboxes) > 0:
        keybox_info()

    app.create_background_task(refresh_device())

    menu_control = Window(
        ScrollableTextControl(
            text=file_list,
            focusable=True,
            get_cursor_position=lambda: Point(0, selectable_rows[selected_index] if len(selectable_rows) > 0 else 0),
            on_scroll=move,
        )
    )
    preview = Window(FormattedTextControl(text=lambda: keybox_info_text, focusable=False))

    # The warning here is due to https://youtrack.jetbrains.com/issue/PY-89873
    @Condition
    def keybox_filter() -> bool:
        return len(keyboxes) > 0

    # The warning here is due to https://youtrack.jetbrains.com/issue/PY-89873
    @Condition
    def device_attached() -> bool:
        return is_android or device is not None

    continue_button = ConditionalContainer(
        Button(text='Continue', handler=lambda: app.exit(result=keyboxes[selected_index])),
        device_attached,
        Button(text='No Device Found'),
    )

    device_info = Window(FormattedTextControl(text=lambda: device_info_text))

    # Keyboard events
    @kb.add(Keys.Up, filter=keybox_filter)
    def _(event: KeyPressEvent) -> None:  # ruff: ignore[unused-function-argument]
        move(-1)

    @kb.add(Keys.Down, filter=keybox_filter)
    def _(event: KeyPressEvent) -> None:  # ruff: ignore[unused-function-argument]
        move(1)

    @kb.add(Keys.Enter, filter=device_attached)
    def _(event: KeyPressEvent) -> None:
        if len(keyboxes) > 0:
            event.app.exit(result=keyboxes[selected_index])

    async def do_download(evt_app: Application[Path | None] | None = None) -> None:
        """Run the `Download` modules from `action.py` and show progress in a dialog.

        Args:
            evt_app: The currently running `Application` (`None` to get automatically)

        """
        nonlocal dialog_shown, dl_dialog
        my_app = evt_app if evt_app is not None else app

        async def run() -> None:
            nonlocal keyboxes, dialog_shown

            dialog_shown = 'progress'
            progress_bar = ProgressBar()
            completed: list[str] = []

            async def update_progress(current: int, total: int, dl_complete: str) -> None:
                progress_bar.percentage = (current * 100) // total
                completed.append(dl_complete)

                # Both lines below are needed to actually draw the progress bar updates
                my_app.invalidate()
                await asyncio.sleep(0)

            root_float.floats.append(
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
            my_app.invalidate()
            await go(*get_downloaders(), progress=update_progress)
            await asyncio.sleep(1)

            root_float.floats.pop()

            keyboxes = [keybox_file async for keybox_file in folder.rglob('*.xml')]
            keybox_info(do_invalidate=True)
            dialog_shown = False

        if can_run():
            await my_app.create_background_task(run())
        else:
            dialog_shown = 'download'

            dl_dialog = AwaitableDialog[Literal['force']](
                title='Notice', body=Window(FormattedTextControl(text='Downloaders can only be ran once every 24hrs'))
            )

            root_float.floats.append(Float(content=dl_dialog))
            if my_app.layout:
                my_app.layout.focus(dl_dialog)
            my_app.invalidate()

            result = await dl_dialog
            dialog_shown = False
            root_float.floats.pop()

            if my_app.layout:
                my_app.layout.focus(menu_control)
            my_app.invalidate()

            if result == 'force':
                force_run()
                await my_app.create_background_task(run())

    async def open_options(evt_app: Application[Path | None] | None = None) -> None:
        """Open the options dialog to set which `Downloader` modules are enabled.

        Args:
            evt_app: The currently running `Application` (`None` to get automatically)

        """
        nonlocal dialog_shown, opts
        dialog_shown = 'options'

        my_app = evt_app if evt_app is not None else app
        opts = Options(is_android=is_android)
        root_float.floats.append(Float(content=opts.dialog))

        if my_app.layout:
            my_app.layout.focus(opts.dialog)
        my_app.invalidate()

        enabled = await opts.future

        if enabled is not None:
            dl_selected = set(enabled)
            all_downloaders: set[type[Downloader]] = Downloader.enabled | Downloader.disabled

            Downloader.enabled.clear()
            Downloader.disabled.clear()

            Downloader.enabled.update(dl_selected)
            Downloader.disabled.update(all_downloaders - dl_selected)

            for dl in all_downloaders:
                overrides.toggle(dl, value=dl in dl_selected)
            overrides.save()

        root_float.floats.pop()

        if my_app.layout:
            my_app.layout.focus(menu_control)
        my_app.invalidate()

        dialog_shown = False

    @kb.add('d')
    async def _(event: KeyPressEvent) -> None:
        await do_download(event.app)

    @kb.add('o')
    async def _(event: KeyPressEvent) -> None:
        await open_options(event.app)

    @kb.add(Keys.F5)
    @kb.add('r')
    async def _(event: KeyPressEvent) -> None:
        await event.app.create_background_task(refresh_device(event.app))

    @kb.add('q')
    def _(event: KeyPressEvent) -> None:
        event.app.exit(result=None)

    @dl_kb.add('f')
    def _(event: KeyPressEvent) -> None:  # ruff: ignore[unused-function-argument]
        dl_dialog.finish('force')

    def status_handler(func: EventFunc) -> Callable[[MouseEvent], Awaitable[None]]:
        async def click(mouse_event: MouseEvent) -> None:
            if (
                mouse_event.button == MouseButton.LEFT
                and mouse_event.event_type == MouseEventType.MOUSE_UP
                and dialog_shown != 'progress'
            ):
                result = func()

                if asyncio.iscoroutine(result):
                    await result

        return click

    status_keys: dict[str, tuple[str, EventFunc]] = {
        'd': ('Run downloaders', do_download),
        'r': ('Reload / Re-scan devices', lambda: app.create_background_task(refresh_device())),
        'o': ('Options', open_options),
        'q': ('Quit', lambda: app.exit(result=None)),
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
        height=2 if is_android else 1,
        style='class:toolbar',
    )

    if is_android:
        root_win = HSplit(
            [
                VSplit(
                    [Frame(menu_control, title='Available Keyboxes'), Frame(device_info, title='Device Info')],
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
                            [Frame(menu_control, title='Available Keyboxes'), Frame(device_info, title='Device Info')],
                            width=Dimension(weight=1),
                        ),
                        Frame(preview, title='Keybox Info', width=Dimension(weight=2)),
                    ]
                ),
                continue_button,
                status_bar,
            ]
        )

    root_float = FloatContainer(content=root_win, floats=[])
    app = Application[Path | None](
        layout=Layout(root_float, focused_element=menu_control),
        full_screen=True,
        key_bindings=merge_key_bindings(
            [
                ConditionalKeyBindings(kb, filter=Condition(lambda: not dialog_shown)),
                ConditionalKeyBindings(dl_kb, filter=Condition(lambda: dialog_shown == 'download')),
            ]
        ),
        mouse_support=Condition(lambda: not is_android),
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

    if not is_android:
        app.output.show_cursor = lambda: None

    if app.layout:
        app.layout.focus(menu_control)

    return await app.run_async()


def menu(context: AbstractAsyncContextManager, *, ignore_empty: bool = False) -> None:
    """Launcher for the file-browser.

    Args:
        context: Context manager to open/close downloaders
        ignore_empty: `True` to allow empty file list, `False` to quit on empty file list

    """

    async def main_menu() -> None:
        async with context:
            selected_file = await select_file(folder.rglob('*.xml'), ignore_empty=ignore_empty)

            if selected_file is None:
                print('Exiting')
            else:
                print(f'Installing {selected_file}')
                selected = folder / selected_file

                if is_android:
                    install = (await (root / f'scripts/{runner["android"]}').absolute(), await selected.absolute())
                    try:
                        await run_process(
                            ['su', 'root', '-c', f'sh {" ".join(str(arg) for arg in install)}'],
                            stdout=sys.stdout,
                            check=True,
                        )
                    except CalledProcessError as e:
                        print(str(e))
                    else:
                        print('Keybox successfully installed')
                elif adb is not None:
                    try:
                        global device

                        if device is None:
                            device = adb.device()

                        if device is not None:
                            # Copy the selected keybox to the tmp folder
                            device.sync.push(selected, key_file)

                            # Also copy the installer script
                            device.sync.push(root / f'scripts/{runner["pc"]}', f'{tmp_folder}/{runner["pc"]}')

                            # Run the main installer script
                            with device.shell(f'su root -c "sh {tmp_folder}/{runner["pc"]}"', stream=True) as stream:
                                print(stream.read_until_close())

                            # Remove the scripts (the keybox was moved already)
                            device.shell(f'rm {tmp_folder}/{runner["pc"]}')
                    except AdbError as e:
                        print(str(e))
                    else:
                        print('Keybox successfully installed')

    asyncio.run(main_menu())
