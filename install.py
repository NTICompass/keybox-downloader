from glob import glob
from pathlib import Path
import inquirer
import sys

is_android = hasattr(sys, 'getandroidapilevel')

if is_android:
    import subprocess
else:
    from adbutils import adb, AdbError

folder = 'keyboxes/valid'
tmp_folder = '/data/local/tmp'
key_file = f'{tmp_folder}/my_keybox.xml'
runner = {'pc': '/install_keybox.sh', 'android': '/install_android.sh'}

if __name__ == '__main__':
    select = inquirer.List(
        'file',
        message='Select an XML file',
        choices=glob('*.xml', root_dir=folder),
        carousel=True,
    )
    args = inquirer.prompt([select])

    try:
        selected = Path(f'{folder}/{args["file"]}')
    except TypeError:
        sys.exit('No file selected')

    if is_android:
        install = (Path(f'scripts/{runner['android']}').absolute(), selected.absolute())
        subprocess.run(['su', 'root', '-c', f'sh {' '.join(str(arg) for arg in install)}'], stdout=sys.stdout)

        print('Keybox successfully installed')
    else:
        try:
            # Connect to the 1st device (throws exception if there are zero or multiple)
            device = adb.device()

            # Copy the selected keybox to the tmp folder
            device.sync.push(selected, key_file)

            # Also copy the installer script
            device.sync.push(Path(f'scripts/{runner["pc"]}'), f'{tmp_folder}/{runner["pc"]}')

            # Run the main installer script
            with device.shell(f'su root -c "sh {tmp_folder}/{runner["pc"]}"', stream=True) as stream:
                print(stream.read_until_close())

            # Remove the scripts (the keybox was moved already)
            device.shell(f'rm {tmp_folder}/{runner["pc"]}')
        except AdbError as e:
            sys.exit(str(e))
        else:
            print('Keybox successfully installed')