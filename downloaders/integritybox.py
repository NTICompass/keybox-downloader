# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""IntegrityBox download module."""

import re
from base64 import b64decode
from codecs import decode
from collections import deque
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

    @override
    def __init__(self) -> None:
        super().__init__()
        self.junk: tuple[str, ...] | None = None

        self.URLS = [
            # Key + Cleanup Scripts
            'github-api:MeowDump/Integrity-Box',
            # Cleanup Script (for extra)
            'github:MeowDump/Integrity-Box::webroot/common_scripts/cleanup.sh',
            # Extra Keybox(es)
            'github:MeowDump/MeowDump::NullVoid/OptimusPrime',
            # https://integritybox.vercel.app/
            'github:freekeybox/mona::meow.tar',
        ]

        github_token = Downloader.get_github_token()
        if github_token:
            self.extra_headers = [{} for _ in self.URLS]
            self.extra_headers[0]['Authorization'] = f'Bearer {github_token}'

    def _get_keybox_url(self, keybox_script: str | bytes) -> str:
        """Extract keybox URL from module's shell scripts.

        Args:
            keybox_script: Text of `key.sh` from module

        Returns:
            Keybox download URL

        """
        keybox_vars = self.get_var_from_shell(keybox_script, ['I', 'J', 'K', 'LOL'])
        return b64decode(keybox_vars['I'] + keybox_vars['J'] + keybox_vars['K'] + keybox_vars['LOL']).decode('ascii')

    @override
    async def process(self, downloaded: AsyncGenerator[str]) -> AsyncGenerator[Keybox | None]:
        self.logger.info('Downloading keybox scripts')

        # The module download and the code in the `main` branch on the repo are slightly different
        download_urls: list[str] = []
        junk_data: deque[tuple[str, ...] | None] = deque()

        zip_dl = await self.get_latest_github_release(await anext(downloaded))
        if zip_dl is not None:
            keybox_script, cleanup_script = self.unzip_files(
                zip_dl, ['webroot/common_scripts/key.sh', 'webroot/common_scripts/cleanup.sh']
            )
            junk_vars = self.get_var_from_shell(cleanup_script, ['X'])

            download_urls.append(self._get_keybox_url(keybox_script))
            junk_data.append(tuple(junk_vars['X'].split(',')))

        # Also download the keybox from the webapp, which is probably the same
        cleanup_script, encoded_keybox, web_keybox = [data async for data in downloaded]

        junk_vars = self.get_var_from_shell(cleanup_script, ['X'])
        junk_data.append(tuple(junk_vars['X'].split(',')))

        keyboxes: list[str | bytes | None] = [web_keybox]

        # Decode the keyboxes
        for encoded in (*[(await self.client.get(dl)).text for dl in download_urls], encoded_keybox):
            self.junk = junk_data.popleft()
            keyboxes.append(self.decode(encoded))

        # Output keyboxes as XML
        for idx, keybox in enumerate(keyboxes):
            if keybox is None:
                yield None
            else:
                try:
                    kb = Keybox(keybox, KeyboxMetadata(source=type(self).__name__, file_idx=idx))

                    keybox_id = kb.device_id
                    if keybox_id is not None:
                        kb.device_id = f'{keybox_id} {idx + 1:d}'

                    yield kb
                except KeyboxError as e:
                    self.logger.info(str(e))
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
