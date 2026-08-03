# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""IntegrityBox download module."""

import re
from base64 import b64decode
from codecs import decode
from typing import TYPE_CHECKING, final, override

from program.keybox import Keybox, KeyboxError, KeyboxMetadata

from . import Downloader

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@final
class IntegrityBox(Downloader):
    """IntegrityBox Downloader.

    Telegram:
    https://t.me/MeowDump

    GitHub:
    https://github.com/MeowDump/Integrity-Box
    """

    DESCRIPTION = 'IntegrityBox module (Mona/MEOWna @ GitHub)'
    URL = 'github-api:MeowDump/Integrity-Box'

    @override
    def __init__(self) -> None:
        super().__init__()

        self.junk: tuple[str, ...] | None = None
        self.extra_headers = Downloader.get_github_token()

    def _get_keybox_url(self, keybox_script: str | bytes) -> str:
        """Extract keybox URL from module's shell scripts.

        Args:
            keybox_script: Text of `key.sh` from module

        Returns:
            Keybox download URL

        """
        keybox_url = self.get_var_from_shell(keybox_script, ['KEYBOX_URL'])
        return keybox_url['KEYBOX_URL']

    @override
    async def process(self, downloaded: AsyncGenerator[str]) -> AsyncGenerator[Keybox | None]:
        self.logger.info('Downloading keybox scripts')

        zip_dl = await self.get_latest_github_release(await anext(downloaded))
        self.extra_headers = None

        if zip_dl is not None:
            keybox_script, cleanup_script = self.unzip_files(
                zip_dl, ['webroot/common_scripts/key.sh', 'webroot/common_scripts/cleanup.sh']
            )

            junk_vars = self.get_var_from_shell(cleanup_script, ['X'])
            self.junk = tuple(junk_vars['X'].split(','))

            # Download / decode the keybox
            keybox = self.decode((await self.client.get(self._get_keybox_url(keybox_script))).text)

            # Output keybox as XML
            try:
                yield Keybox(keybox, KeyboxMetadata(source=type(self).__name__))
            except KeyboxError as e:
                self.logger.info(str(e))
                yield None
        else:
            yield None

    @override
    def decode(self, encoded: str) -> str:
        self.logger.info('Decoding keybox xml')

        # Decode base64 ten times!
        for _i in range(10):
            encoded = b64decode(encoded).decode('ascii')

        # Then decode the hex bytes
        encoded = bytes.fromhex(encoded).decode('utf-8')

        # Next use rot13
        encoded = decode(encoded, 'rot_13')

        # Remove extra "junk" from the file
        if self.junk is not None:
            encoded = re.sub(rf'({"|".join(self.junk)})', '', encoded)

        # Finally remove extra comments/newlines
        return encoded.replace('<!--INTEGRITY BOX-->', '')
