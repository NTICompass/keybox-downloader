# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""TrickyAddon download module."""

from base64 import b64decode
from typing import final, override

from . import Downloader


@final
class TrickyAddon(Downloader, enabled=False):
    """TrickyAddon Downloader.

    Telegram:
    https://t.me/s/kowchannel

    GitHub:
    https://github.com/KOWX712/Tricky-Addon-Update-Target-List

    Keybox Repo:
    https://keybox.kowx712.cc/
    """

    DESCRIPTION = 'Tricky Addon - Update Target List module (KOWX712 @ GitHub)'
    URL = 'github:KOWX712/Tricky-Addon-Update-Target-List:keybox:.extra'

    """
    TODO: This module now uses its own Keybox repo: https://keybox.kowx712.cc
    This is written using React, so it may make scraping hard
    
    Though the downloads are via the API:
    https://keybox.kowx712.cc/api/keyboxes/43/download
    (Might need cloudscraper)
    
    So maybe we can just hit the API directly:
    https://keybox.kowx712.cc/api/keyboxes?search=43&sort=status&page=1&limit=10
    https://keybox.kowx712.cc/api/keyboxes?search=&sort=status&page=1&limit=10
    
    See: https://github.com/KOWX712/Tricky-Addon-Update-Target-List/blob/main/webui/src/keybox/repo/repo-api.md#optional-backend-api-structure
    """

    @override
    def decode(self, encoded: str) -> str:
        self.logger.info('Decoding keybox xml')

        # First decode the hex bytes
        encoded = bytes.fromhex(encoded).decode('ascii')

        # Then base64 decode
        return b64decode(encoded).decode('ascii')
