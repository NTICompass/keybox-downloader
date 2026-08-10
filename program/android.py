# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Abstracts out running commands on a phone."""

import sys
from contextlib import suppress
from typing import TYPE_CHECKING, ClassVar

try:
    from adbutils import AdbError, adb

    if TYPE_CHECKING:
        from adbutils import AdbDevice
except ImportError as err:
    if hasattr(sys, 'getandroidapilevel'):
        from subprocess import CalledProcessError

        from anyio import run_process
    else:
        msg = 'adbutils is required on PC'
        raise RuntimeError(msg) from err


class Android:
    """Commands are either ran via adb or subprocess."""

    is_android: ClassVar[bool] = hasattr(sys, 'getandroidapilevel')
    device: AdbDevice | None = None

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
        if not self.is_android and adb is not None:
            with suppress(AdbError):
                if self.device is None:
                    # Connect to the 1st device (throws exception if there are zero or multiple)
                    self.device = adb.device()

                if self.device is not None:
                    return str(self.device.getprop(prop) if prop is not None else self.device.prop).strip()
        return ''
