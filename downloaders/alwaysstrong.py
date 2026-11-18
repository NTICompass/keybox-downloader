# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""AlwaysStrong download module."""

from base64 import b64decode
from typing import final, override

from . import Downloader


@final
class AlwaysStrong(Downloader):
    """AlwaysStrong Downloader.

    Telegram:
    https://t.me/s/keyboxstrong
    https://t.me/evokeroot
    https://t.me/evokerr

    GitLab:
    https://gitlab.com/Evokerr/AlwaysStrong
    """

    DESCRIPTION = 'AlwaysStrong module (Evokerr @ GitLab)'
    URL = 'https://evoker.qzz.io/key'

    @override
    def __init__(self) -> None:
        super().__init__()
        self.extra_headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android) asfetch/1.0'}

    @override
    def decode(self, encoded: str) -> str:
        return b64decode(encoded).decode('ascii')
