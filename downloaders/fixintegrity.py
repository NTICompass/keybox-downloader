# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""FixIntegrity/TrickBox download module."""

from base64 import b64decode
from typing import final, override

from . import Downloader


@final
class FixIntegrity(Downloader):
    """FixIntegrity (also called TrickyBox/TrickBox) Downloader.

    Telegram:
    https://t.me/s/randommodules
    https://t.me/s/CollectionByCharlie

    GitHub:
    https://github.com/GueRapii/FixIntegrity
    https://github.com/GueRapii/TrickBox
    """

    DESCRIPTION = 'FixIntegrity or TrickBox module (GueRapii @ GitHub)'
    URL = 'github:GueRapii/randommodulesfiles::file.enc'

    @override
    def decode(self, encoded: str) -> str:
        return b64decode(encoded).decode('ascii')
