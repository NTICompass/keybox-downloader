from adbutils import adb, AdbError
from glob import glob
from pathlib import Path
import inquirer
import sys

folder = 'keyboxes/valid'
tmp_folder = '/data/local/tmp'
key_file = f'{tmp_folder}/my_keybox.xml'
runner = f'{tmp_folder}/install_keybox.sh'

if __name__ == '__main__':
    select = inquirer.List(
        'file',
        message='Select an XML file',
        choices=glob('*.xml', root_dir=folder),
        carousel=True,
    )
    args = inquirer.prompt([select])
    scripts = glob('*.sh', root_dir='scripts')

    try:
        # Connect to the 1st device (throws exception if there are zero or multiple)
        device = adb.device()

        # Copy the selected keybox to the tmp folder
        device.sync.push(Path(f'{folder}/{args["file"]}'), key_file)

        # Also copy the installer script(s)
        for script in scripts:
            device.sync.push(Path(f'scripts/{script}'), f'{tmp_folder}/{script}')

        # Run the main installer script
        install = device.shell(f'su root -c "sh {runner}"')
        print(install)

        # Remove the scripts (the keybox was moved already)
        for script in scripts:
            device.shell(f'rm {tmp_folder}/{script}')
    except TypeError:
        sys.exit('No file selected')
    except AdbError as e:
        sys.exit(str(e))
    else:
        print('Keybox successfully installed')
