from glob import glob
from pathlib import Path
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame
from utils.certs import Certs
from xml.etree.ElementTree import Element
import sys
import xml.etree.ElementTree as ET


is_android = hasattr(sys, 'getandroidapilevel')

if is_android:
    import subprocess
else:
    from adbutils import adb, AdbError

folder = 'keyboxes/valid'
tmp_folder = '/data/local/tmp'
key_file = f'{tmp_folder}/my_keybox.xml'
runner = {'pc': 'install_keybox.sh', 'android': 'install_android.sh'}
certs = Certs()
files: dict[str, Element] = {}


def get_cert_serial(file: str) -> int:
    if file not in files:
        files[file] = ET.parse(Path(f'{folder}/{file}')).getroot()

    serials = [
        cert.serial_number
        for cert in certs.get_certs(keybox=files[file])
        if cert.signature_algorithm_oid.dotted_string == '1.2.840.10045.4.3.2'
    ]

    return serials[0] if len(serials) > 0 else 0


def get_cert_counts(file: str) -> str:
    if file not in files:
        files[file] = ET.parse(Path(f'{folder}/{file}')).getroot()

    ec_certs, rsa_certs = certs.get_counts(keybox=files[file])
    return f'{ec_certs} EC certs, {rsa_certs} RSA certs'


def select_file(keyboxes: list[str]) -> str | None:
    selected_index = 0
    kb = KeyBindings()
    menu_control = FormattedTextControl(
        text=lambda: '\n'.join(
            f'{"->" if idx == selected_index else "  "} {file}'
            for idx, file in enumerate(keyboxes)
        )
    )
    preview = FormattedTextControl(
        text=lambda: (
            f'{keyboxes[selected_index]}: {get_cert_serial(keyboxes[selected_index]):x}'
        ),
        focusable=False,
    )

    def move(delta: int):
        nonlocal selected_index
        selected_index = (selected_index + delta) % len(keyboxes)

    @kb.add('up')
    def _(event):
        move(-1)
        # event.app.invalidate()

    @kb.add('down')
    def _(event):
        move(1)
        # event.app.invalidate()

    @kb.add('enter')
    def _(event):
        event.app.exit(result=keyboxes[selected_index])

    @kb.add('q')
    def _(event):
        event.app.exit(result=None)

    if is_android:
        root = HSplit(
            [
                Frame(Window(menu_control), title='Valid Keyboxes'),
                Frame(Window(preview), title='Keybox Info'),
            ]
        )
    else:
        root = VSplit(
            [
                Frame(Window(menu_control), title='Valid Keyboxes'),
                Frame(Window(preview), title='Keybox Info'),
            ]
        )

    app = Application(layout=Layout(root), key_bindings=kb, full_screen=True)
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
                # Connect to the 1st device (throws exception if there are zero or multiple)
                device = adb.device()

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
