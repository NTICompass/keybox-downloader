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

    try:
        device = adb.device()

        device.sync.push(Path(f'{folder}/{args["file"]}'), key_file)
        for script in glob('*.sh', root_dir='scripts'):
            device.sync.push(Path(f'scripts/{script}'), f'{tmp_folder}/{script}')

        print(device.shell(f'su root -c "sh {runner}"'))
        for script in glob('*.sh', root_dir='scripts'):
            device.shell(f'rm {tmp_folder}/{script}')
    except TypeError:
        sys.exit('No file selected')
    except RuntimeError:
        sys.exit('Multiple devices found')
    except AdbError as e:
        sys.exit(str(e))
    else:
        print('Keybox successfully installed')
