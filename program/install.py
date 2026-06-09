from .action import get_downloaders, go
from .options import Options
from cache_data import Overrides
from collections.abc import Callable
from downloaders import Downloader
from pathlib import Path
from program.keybox import Keybox
from prompt_toolkit.application import Application, get_app, in_terminal
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.key_binding import (
    KeyBindings,
    KeyPressEvent,
    ConditionalKeyBindings,
)
from prompt_toolkit.layout import (
    Layout,
    HSplit,
    VSplit,
    Window,
    ConditionalContainer,
    Float,
    FloatContainer,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseButton, MouseEventType, MouseEvent
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame, Button
import __main__
import asyncio
import sys

is_android = hasattr(sys, 'getandroidapilevel')

try:
    from adbutils import adb, AdbDevice, AdbError

    device: AdbDevice | None
except ImportError:
    if is_android:
        import subprocess
    else:
        raise RuntimeError('adbutils is required on PC')
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


async def get_prop(prop: str | None = None) -> str:
    global device

    if is_android and prop is not None:
        proc = await asyncio.create_subprocess_exec(
            '/system/bin/getprop',
            prop,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        return stdout.decode().strip() if stdout else ''
    elif not is_android and adb is not None:
        try:
            if device is None:
                # Connect to the 1st device (throws exception if there are zero or multiple)
                device = adb.device()

            if device is not None:
                return str(
                    device.getprop(prop) if prop is not None else device.prop
                ).strip()
            else:
                raise RuntimeError('No device found')
        except (AdbError, RuntimeError):
            return ''
    else:
        return ''


async def get_device() -> str:
    global device

    if is_android:
        return await get_prop('ro.system.build.fingerprint')
    else:
        manufacturer, fingerprint = await asyncio.gather(
            get_prop('ro.product.manufacturer'),
            get_prop('ro.system.build.fingerprint'),
        )
        props = '\n'.join(
            [
                await get_prop('ro.vendor.asus.product.mkt_name')
                if manufacturer == 'asus'
                else await get_prop(),
                fingerprint,
            ]
        )

        return props if props.strip() != '' else 'No device found, press "r" to re-try'


def get_cert_serials(file: Path) -> list[str]:
    if file.name not in files:
        files[file.name] = Keybox(file)

    all_certs = [
        f'{cert} ({"Valid" if valid else "Revoked"})'
        for cert, valid in files[file.name].keys_valid.items()
    ]
    ec_certs, rsa_certs = files[file.name].key_counts

    return [
        f'{ec_certs} EC certs, {rsa_certs} RSA certs',
        *all_certs,
    ]


async def select_file(keyboxes: list[Path], ignore_empty=False) -> Path | None:
    if not ignore_empty and len(keyboxes) == 0:
        print('No valid keyboxes found')
        return None

    await Keybox.init_attestation(Downloader.client)

    selected_index = 0
    device_info_text = ''
    keybox_info_text = ''
    options_shown = False

    kb = KeyBindings()
    opts: Options
    menu_control: Window
    root_float: FloatContainer

    async def refresh_device(event: KeyPressEvent | None = None):
        nonlocal device_info_text
        device_info_text = await get_device()

        if event is not None:
            event.app.invalidate()
        else:
            get_app().invalidate()

    async def keybox_info(event: KeyPressEvent | MouseEvent | None = None):
        nonlocal keybox_info_text

        keybox_info_text = (
            f'{keyboxes[selected_index].parent.name} / {keyboxes[selected_index].name}: {"\n".join(get_cert_serials(keyboxes[selected_index]))}'
            if len(keyboxes) > 0
            else ''
        )

        if event is None:
            get_app().invalidate()

    def file_list() -> StyleAndTextTuples:
        def handler(idx: int) -> Callable[[MouseEvent], None]:
            def click(mouse_event: MouseEvent):
                nonlocal selected_index

                if (
                    mouse_event.button == MouseButton.LEFT
                    and mouse_event.event_type == MouseEventType.MOUSE_UP
                ):
                    selected_index = idx
                    get_app().create_background_task(keybox_info(mouse_event))

            return click

        return [
            # (style, text, handler)
            (
                'class:selected' if idx == selected_index else '',
                f'{"->" if idx == selected_index else "  "} {file.parent.name} / {file.name}\n',
                handler(idx),
            )
            for idx, file in enumerate(keyboxes)
        ]

    if len(keyboxes) > 0:
        get_app().create_background_task(keybox_info())

    get_app().create_background_task(refresh_device())

    menu_control = Window(
        FormattedTextControl(
            text=file_list,
            focusable=True,
            get_cursor_position=lambda: Point(0, selected_index),
        )
    )
    preview = Window(
        FormattedTextControl(text=lambda: keybox_info_text, focusable=False)
    )

    continue_button = ConditionalContainer(
        Button(
            text='Continue',
            handler=lambda: get_app().exit(result=keyboxes[selected_index]),
        ),
        Condition(lambda: is_android or device is not None),
        Button(text='No Device Found'),
    )

    device_info = Window(FormattedTextControl(text=lambda: device_info_text))

    def move(delta: int, event: KeyPressEvent):
        nonlocal selected_index
        selected_index = (selected_index + delta) % len(keyboxes)
        event.app.create_background_task(keybox_info(event))

    @kb.add('up', filter=Condition(lambda: len(keyboxes) > 0))
    def _(event: KeyPressEvent):
        move(-1, event)

    @kb.add('down', filter=Condition(lambda: len(keyboxes) > 0))
    def _(event: KeyPressEvent):
        move(1, event)

    @kb.add('enter', filter=Condition(lambda: is_android or device is not None))
    def _(event: KeyPressEvent):
        if len(keyboxes) > 0:
            event.app.exit(result=keyboxes[selected_index])

    @kb.add('d')
    def _(event: KeyPressEvent):
        async def run():
            async with in_terminal():
                nonlocal keyboxes

                await go(*get_downloaders())
                keyboxes = list(folder.rglob('*.xml'))
                await keybox_info(event)

        event.app.create_background_task(run())

    @kb.add('o')
    async def _(event: KeyPressEvent):
        nonlocal options_shown, opts
        options_shown = True

        opts = Options()
        root_float.floats.append(Float(content=opts.dialog))

        if event.app.layout:
            event.app.layout.focus(opts.dialog)
        event.app.invalidate()

        enabled = await opts.future

        if enabled is not None:
            dl_selected = set(enabled)
            all_downloaders: set[type[Downloader]] = (
                Downloader.enabled | Downloader.disabled
            )

            Downloader.enabled.clear()
            Downloader.disabled.clear()

            Downloader.enabled.update(dl_selected)
            Downloader.disabled.update(all_downloaders - dl_selected)

            for dl in all_downloaders:
                overrides.toggle(dl, dl in dl_selected)
            overrides.save()

        root_float.floats.pop()

        if event.app.layout:
            event.app.layout.focus(menu_control)
        event.app.invalidate()

        options_shown = False

    @kb.add('r')
    def _(event: KeyPressEvent):
        event.app.create_background_task(refresh_device(event))

    @kb.add('q')
    def _(event: KeyPressEvent):
        event.app.exit(result=None)

    if is_android:
        root_win = HSplit(
            [
                VSplit(
                    [
                        Frame(menu_control, title='Valid Keyboxes'),
                        Frame(device_info, title='Device Info'),
                    ]
                ),
                Frame(preview, title='Keybox Info'),
            ]
        )
    else:
        root_win = HSplit(
            [
                VSplit(
                    [
                        HSplit(
                            [
                                Frame(menu_control, title='Valid Keyboxes'),
                                Frame(device_info, title='Device Info'),
                            ]
                        ),
                        Frame(preview, title='Keybox Info'),
                    ]
                ),
                continue_button,
            ]
        )

    root_float = FloatContainer(content=root_win, floats=[])
    app = Application(
        layout=Layout(root_float, focused_element=menu_control),
        full_screen=True,
        key_bindings=ConditionalKeyBindings(
            kb,
            filter=Condition(lambda: not options_shown),
        ),
        mouse_support=Condition(lambda: not is_android),
        style=Style.from_dict(
            {
                'checkbox': 'fg:black',
                'checkbox-checked': 'fg:red bold',
                'checkbox-selected': 'reverse bold',
            }
        ),
    )

    if not is_android:
        app.output.show_cursor = lambda: None

    if app.layout:
        app.layout.focus(menu_control)

    return await app.run_async()


def menu(ignore_empty=False):
    selected_file = asyncio.run(
        select_file(list(folder.rglob('*.xml')), ignore_empty=ignore_empty)
    )

    if selected_file is None:
        print('Exiting')
    else:
        print(f'Installing {selected_file}')
        selected = folder / selected_file

        if is_android:
            install = (
                (root / f'scripts/{runner["android"]}').absolute(),
                selected.absolute(),
            )
            subprocess.run(
                ['su', 'root', '-c', f'sh {" ".join(str(arg) for arg in install)}'],
                stdout=sys.stdout,
            )

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
                    device.sync.push(
                        root / f'scripts/{runner["pc"]}', f'{tmp_folder}/{runner["pc"]}'
                    )

                    # Run the main installer script
                    with device.shell(
                        f'su root -c "sh {tmp_folder}/{runner["pc"]}"', stream=True
                    ) as stream:
                        print(stream.read_until_close())

                    # Remove the scripts (the keybox was moved already)
                    device.shell(f'rm {tmp_folder}/{runner["pc"]}')
            except AdbError as e:
                sys.exit(str(e))
            else:
                print('Keybox successfully installed')
