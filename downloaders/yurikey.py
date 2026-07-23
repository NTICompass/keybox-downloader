# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""YuriKey download module."""

from base64 import b64decode
from typing import final, override

from . import Downloader


@final
class YuriKey(Downloader):
    """IntegrityBox Downloader.

    Telegram:
    https://t.me/s/yuriiroot
    https://t.me/s/yuriservice

    GitHub:
    https://Yurii0307/yurikey
    """

    DESCRIPTION = 'YuriKey module (Yurii0307 @ GitHub)'
    URL = 'github:Yurii0307/yurikey::key'

    @override
    def decode(self, encoded: str) -> str:
        return b64decode(encoded).decode('ascii')
