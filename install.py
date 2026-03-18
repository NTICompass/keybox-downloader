from glob import glob
from pathlib import Path
from utils.certs import Certs
import inquirer
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


def get_cert_serial(file: str) -> int:
    cert_file = ET.parse(Path(f'{folder}/{file}'))
    serials = [
        cert.serial_number
        for cert in certs.get_certs(keybox=cert_file.getroot())
        if cert.signature_algorithm_oid.dotted_string == '1.2.840.10045.4.3.2'
    ]

    return serials[0] if len(serials) > 0 else 0


if __name__ == '__main__':
    selected_file: str = inquirer.list_input(
        'Select an XML file',
        choices=[
            # (string to show in list, string to return from selection)
            (f'{file} ({get_cert_serial(file):x})', file)
            for file in glob('*.xml', root_dir=folder)
        ],
        carousel=True,
    )

    print(f'Installing {selected_file}')
    selected = Path(f'{folder}/{selected_file}')

    if is_android:
        install = (Path(f'scripts/{runner["android"]}').absolute(), selected.absolute())
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
