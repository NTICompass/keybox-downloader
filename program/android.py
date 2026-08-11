# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Abstracts out running commands on a phone."""

import sys
from contextlib import suppress
from functools import cached_property
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
