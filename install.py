from glob import glob
from pathlib import Path
from prompt_toolkit.application import Application, get_app
from prompt_toolkit.filters import Condition, Filter
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, ConditionalContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseButton, MouseEventType, MouseEvent
from prompt_toolkit.widgets import Frame, Button
from typing import Callable
from utils.certs import Certs
from xml.etree.ElementTree import Element
import sys
import xml.etree.ElementTree as ET


is_android = hasattr(sys, 'getandroidapilevel')

if is_android:
    import subprocess

    device = None
else:
    from adbutils import adb, AdbError, AdbDevice

    device: AdbDevice | None = None

folder = 'keyboxes/valid'
tmp_folder = '/data/local/tmp'
key_file = f'{tmp_folder}/my_keybox.xml'
runner = {'pc': 'install_keybox.sh', 'android': 'install_android.sh'}

current_keybox: Element | None = None
certs = Certs()
files: dict[str, Element] = {}


def get_device() -> str:
    global device

    if is_android:
        name = subprocess.run(
            ['getprop', 'ro.system.build.fingerprint'],
            capture_output=True,
            text=True,
        )

        return name.stdout
    else:
        try:
            # Connect to the 1st device (throws exception if there are zero or multiple)
            device = adb.device()

            if device is not None:
                return '\n'.join(
                    [
                        device.getprop('ro.vendor.asus.product.mkt_name')
                        if device.getprop('ro.product.manufacturer') == 'asus'
                        else str(device.prop),
                        device.getprop('ro.system.build.fingerprint'),
                    ]
                )
            else:
                raise RuntimeError('device is None')
        except (AdbError, RuntimeError):
            return 'No device found, press "r" to re-try'


def get_cert_serials(file: str) -> list[str]:
    if file not in files:
        files[file] = ET.parse(Path(f'{folder}/{file}')).getroot()

    all_certs = [
        f'{cert.serial_number:x}' for cert in certs.get_certs(keybox=files[file])
    ]
    ec_certs, rsa_certs = certs.get_counts(keybox=files[file])

    return [
        f'{ec_certs} EC certs, {rsa_certs} RSA certs',
        *all_certs,
    ]


def select_file(keyboxes: list[str]) -> str | None:
    selected_index = 0
    kb = KeyBindings()

    def file_list() -> StyleAndTextTuples:
        def handler(idx: int) -> Callable[[MouseEvent], None]:
            def click(mouse_event: MouseEvent):
                nonlocal selected_index

                if (
                    mouse_event.button == MouseButton.LEFT
                    and mouse_event.event_type == MouseEventType.MOUSE_UP
                ):
                    selected_index = idx

            return click

        return [
            # (style, text, handler)
            (
                'class:selected' if idx == selected_index else '',
                f'{"->" if idx == selected_index else "  "} {file}\n',
                handler(idx),
            )
            for idx, file in enumerate(keyboxes)
        ]

    menu_control = Window(FormattedTextControl(text=file_list))
    preview = Window(
        FormattedTextControl(
            text=lambda: (
                f'{keyboxes[selected_index]}: {"\n".join(get_cert_serials(keyboxes[selected_index]))}'
            ),
            focusable=False,
        )
    )

    can_continue: Filter = Condition(lambda: is_android or device is not None)
    continue_button = ConditionalContainer(
        Button(
            text='Continue',
            handler=lambda: get_app().exit(result=keyboxes[selected_index]),
        ),
        can_continue,
        Button(text='No Device Found'),
    )
    device_info = Window(FormattedTextControl(text=get_device))

    def move(delta: int):
        nonlocal selected_index

        selected_index = (selected_index + delta) % len(keyboxes)

    @kb.add('up')
    def _(event: KeyPressEvent):
        move(-1)

    @kb.add('down')
    def _(event: KeyPressEvent):
        move(1)

    @kb.add('enter', filter=can_continue)
    def _(event: KeyPressEvent):
        event.app.exit(result=keyboxes[selected_index])

    @kb.add('r')
    def _(event: KeyPressEvent):
        event.app.invalidate()

    @kb.add('q')
    def _(event: KeyPressEvent):
        event.app.exit(result=None)

    if is_android:
        root = HSplit(
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
        root = HSplit(
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

    app = Application(
        layout=Layout(root, focused_element=menu_control),
        full_screen=True,
        key_bindings=kb,
        mouse_support=not is_android,
    )

    if not is_android:
        app.output.show_cursor = lambda: None

    return app.run()


if __name__ == '__main__':
    selected_file = select_file(glob('*.xml', root_dir=folder))

    if selected_file is None:
        print('Exiting')
    else:
        print(f'Installing {selected_file}')
        selected = Path(f'{folder}/{selected_file}')

        if is_android:
            install = (
                Path(f'scripts/{runner["android"]}').absolute(),
                selected.absolute(),
            )
            subprocess.run(
                ['su', 'root', '-c', f'sh {" ".join(str(arg) for arg in install)}'],
                stdout=sys.stdout,
            )

            print('Keybox successfully installed')
        else:
            try:
                if device is None:
                    # Connect to the 1st device (throws exception if there are zero or multiple)
                    device = adb.device()

                if device is not None:
                    # Copy the selected keybox to the tmp folder
                    device.sync.push(selected, key_file)

                    # Also copy the installer script
                    device.sync.push(
                        Path(f'scripts/{runner["pc"]}'), f'{tmp_folder}/{runner["pc"]}'
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
