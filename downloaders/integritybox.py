from . import Downloader
from base64 import b64decode
from codecs import decode
from collections.abc import AsyncGenerator
from program.keybox import Keybox, KeyboxMetadata, KeyboxError
from typing import final, override
import re


@final
class IntegrityBox(Downloader):
    # https://t.me/MeowDump
    URLS = [
        # Key Script
        'github:MeowDump/Integrity-Box::webroot/common_scripts/key.sh',
        # Cleanup Script
        'github:MeowDump/Integrity-Box::webroot/common_scripts/cleanup.sh',
        # Extra Keybox(es)
        'github:MeowDump/MeowDump::NullVoid/OptimusPrime',
        # https://integritybox.vercel.app/
        'github:freekeybox/mona::meow.tar',
    ]

    @override
    def __init__(self):
        super().__init__()
        self.junk: list[str] = []

    @property
    @override
    def description(self) -> str:
        return 'IntegrityBox module (Mona/MEOWna @ GitHub)'

    def get_keybox_url(self, keybox_script: str | bytes) -> str:
        keybox_vars = self.get_var_from_shell(keybox_script, ['I', 'J', 'K', 'LOL'])
        return b64decode(
            keybox_vars['I'] + keybox_vars['J'] + keybox_vars['K'] + keybox_vars['LOL']
        ).decode('ascii')

    @override
    async def process(
        self, downloaded: AsyncGenerator[str]
    ) -> AsyncGenerator[Keybox | None]:
        self.logger.info('Downloading keybox scripts')

        # Also download the keybox from the webapp, which is probably the same
        keybox_script, cleanup_script, encoded_keybox, web_keybox = [
            data async for data in downloaded
        ]

        download_url = self.get_keybox_url(keybox_script)
        junk_vars = self.get_var_from_shell(cleanup_script, ['X'])
        self.junk = junk_vars['X'].split(',')

        keyboxes: list[str | bytes | None] = [web_keybox]

        # Decode the keyboxes
        for encoded in (
            (await self.client.get(download_url)).text,
            encoded_keybox,
        ):
            keyboxes.append(self.decode(encoded))

        # Output keyboxes as XML
        for idx, keybox in enumerate(keyboxes):
            if keybox is None:
                yield None
            else:
                try:
                    kb = Keybox(
                        keybox,
                        KeyboxMetadata(source=type(self).__name__, file_idx=idx),
                    )

                    keybox_id = kb.device_id
                    if keybox_id is not None:
                        kb.device_id = f'{keybox_id} {idx + 1:d}'

                    yield kb
                except KeyboxError as e:
                    self.logger.info(e.msg)
                    yield None

    @override
    def decode(self, encoded: str) -> str | None:
        self.logger.info('Decoding keybox xml')

        # Decode base64 ten times!
        for i in range(10):
            encoded = b64decode(encoded).decode('ascii')

        # Then decode the hex bytes
        encoded = bytes.fromhex(encoded).decode('utf-8')

        # Next use rot13
        encoded = decode(encoded, 'rot_13')

        # Remove extra "junk" from the file
        encoded = re.sub(rf'({"|".join(self.junk)})', '', encoded)

        # Finally remove extra comments/newlines
        return encoded.replace('<!--INTEGRITY BOX-->', '')
