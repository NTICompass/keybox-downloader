from . import Downloader, fix_rsa_keys
from base64 import b64decode
from collections.abc import AsyncGenerator
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET


class TrickyAddon(Downloader):
    # https://t.me/s/kowchannel
    # This URL is different from other GitHub URLs
    URL = 'https://raw.githubusercontent.com/KOWX712/Tricky-Addon-Update-Target-List/keybox/.extra'

    async def get_keybox(self) -> AsyncGenerator[Element | None]:
        self.logger.info('Downloading encoded keybox')
        self.encoded = str(await anext(self.download_urls()))

        yield fix_rsa_keys(
            ET.fromstring(self.decode_keybox())
            if len(self.encoded is not None and self.encoded.strip()) > 0
            else None
        )

    def decode_keybox(self) -> str:
        self.logger.info('Decoding keybox xml')

        # First decode the hex bytes
        encoded = bytes.fromhex(
            self.encoded if self.encoded is not None else ''
        ).decode('ascii')

        # Then base64 decode
        return b64decode(encoded).decode('ascii')
