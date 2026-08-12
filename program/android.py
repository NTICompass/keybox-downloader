# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Abstracts out running commands on a phone."""

import sys
from contextlib import suppress
from functools import cached_property
from pathlib import Path as SysPath
from typing import TYPE_CHECKING, ClassVar, final

import __main__

from .helpers import gather

if TYPE_CHECKING:
    from anyio import Path

# Use `subprocess` on Android
if hasattr(sys, 'getandroidapilevel'):
    from subprocess import CalledProcessError

    from anyio import run_process
# Use `adb` on PC
else:
    try:
        from adbutils import AdbError, adb

        if TYPE_CHECKING:
            from adbutils import AdbDevice
    except ImportError as err:
        msg = 'adbutils is required on PC'
        raise RuntimeError(msg) from err

root: Path = __main__.root
tmp_folder = '/data/local/tmp'
key_file = f'{tmp_folder}/my_keybox.xml'
runner = {'pc': 'install_keybox.sh', 'android': 'install_android.sh'}


@final
class Android:
    """Commands are either ran via adb or subprocess."""

    is_android: ClassVar[bool] = hasattr(sys, 'getandroidapilevel')

    @cached_property
    def device(self) -> AdbDevice | None:
        """Connect to an Android device via adb.

        Returns:
            An `AdbDevice` if you are on a PC and an Android device is connected.

        """
        try:
            return adb.device() if not self.is_android else None
        except AdbError:
            return None

    def reset_device(self) -> None:
        """Invalidate the cache and re-connect to a device."""
        if not self.is_android and hasattr(self, 'device'):
            del self.device

    async def get_prop(self, prop: str | None = None) -> str:
        """Get a property value from the currently connected Android phone (or the phone we're running on).

        Args:
            prop: The property name, like "ro.system.build.fingerprint"

        Returns:
            The property value

        """
        if self.is_android and prop is not None:
            with suppress(CalledProcessError):
                proc = await run_process(['/system/bin/getprop', prop], check=True)
                return proc.stdout.decode().strip()

        # If we're on a PC, then try to connect via adb
        device = self.device

        if device is not None:
            return str(device.getprop(prop) if prop is not None else device.prop).strip()

        return ''

    async def install(self, file: Path) -> None:
        """Install a keybox: On Android, call the scripts via `subprocess` otherwise use adb.

        Args:
            file: Keybox file to install.

        """
        if self.is_android:
            install = await gather((root / f'scripts/{runner["android"]}').absolute(), file.absolute())

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
        else:
            try:
                device = self.device

                if device is not None:
                    # Copy the selected keybox to the tmp folder
                    device.sync.push(SysPath(file), key_file)

                    # Also copy the installer script
                    device.sync.push(SysPath(root / f'scripts/{runner["pc"]}'), f'{tmp_folder}/{runner["pc"]}')

                    # Run the main installer script
                    with device.shell(f'su root -c "sh {tmp_folder}/{runner["pc"]}"', stream=True) as stream:
                        print(stream.read_until_close())

                    # Remove the scripts (the keybox was moved already)
                    device.shell(f'rm {tmp_folder}/{runner["pc"]}')
            except AdbError as e:
                print(str(e))
            else:
                print('Keybox successfully installed')
