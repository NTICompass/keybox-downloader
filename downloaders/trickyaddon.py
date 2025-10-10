from base64 import b64decode
from downloaders.downloader import Downloader
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET


class TrickyAddon(Downloader):
    URL = 'https://github.com/KOWX712/Tricky-Addon-Update-Target-List/raw/refs/heads/main/.extra'

    async def get_keybox(self) -> Element | None:
        self.logger.info('Downloading encoded keybox')

        self.encoded = await anext(self.download_urls())
        return ET.fromstring(self.decode_keybox()) if len(self.encoded) > 0 else None

    def decode_keybox(self) -> str:
        self.logger.info('Decoding keybox xml')

        # First decode the hex bytes
        encoded = bytes.fromhex(self.encoded).decode('ascii')

        # Then base64 decode
        return b64decode(encoded).decode('ascii')