# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Actually copy/install the keybox onto a phone."""

import sys
from pathlib import Path as SysPath
from typing import TYPE_CHECKING, final

import __main__

from .android import Android
from .helpers import gather

if TYPE_CHECKING:
    from anyio import Path

root: Path = __main__.root
tmp_folder = '/data/local/tmp'
key_file = f'{tmp_folder}/my_keybox.xml'
runner = {'pc': 'install_keybox.sh', 'android': 'install_android.sh'}


@final
class Installer:
    """Install the keybox on a phone, either using adb or `subprocess`."""

    device: AdbDevice | None = None

    def __init__(self, file: Path) -> None:
        """Initialize the installer with the specific file."""
        self._selected_file = file

    async def go(self) -> None:
        """On Android, call the script via `subprocess` otherwise use adb.

        Renamed to `go()` from `__call__()` due to PyCharm bug:
        https://youtrack.jetbrains.com/issue/PY-89873
        """
        if Android.is_android:
            install = await gather((root / f'scripts/{runner["android"]}').absolute(), self._selected_file.absolute())
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
                if self.device is None:
                    self.device = adb.device()

                if self.device is not None:
                    # Copy the selected keybox to the tmp folder
                    self.device.sync.push(SysPath(self._selected_file), key_file)

                    # Also copy the installer script
                    self.device.sync.push(SysPath(root / f'scripts/{runner["pc"]}'), f'{tmp_folder}/{runner["pc"]}')

                    # Run the main installer script
                    with self.device.shell(f'su root -c "sh {tmp_folder}/{runner["pc"]}"', stream=True) as stream:
                        print(stream.read_until_close())

                    # Remove the scripts (the keybox was moved already)
                    self.device.shell(f'rm {tmp_folder}/{runner["pc"]}')
            except AdbError as e:
                print(str(e))
            else:
                print('Keybox successfully installed')
