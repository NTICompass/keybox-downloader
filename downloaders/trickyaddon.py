# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""TrickyAddon download module."""

from base64 import b64decode
from typing import final, override

from . import Downloader


@final
class TrickyAddon(Downloader):
    """TrickyAddon Downloader.

    Telegram:
    https://t.me/s/kowchannel

    GitHub:
    https://github.com/MeowDump/Integrity-Box
    """

    DESCRIPTION = 'Tricky Addon - Update Target List module (KOWX712 @ GitHub)'
    URL = 'github:KOWX712/Tricky-Addon-Update-Target-List:keybox:.extra'

    @override
    def decode(self, encoded: str) -> str:
        self.logger.info('Decoding keybox xml')

        # First decode the hex bytes
        encoded = bytes.fromhex(encoded).decode('ascii')

        # Then base64 decode
        return b64decode(encoded).decode('ascii')
