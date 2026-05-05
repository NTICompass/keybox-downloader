from . import Downloader
from base64 import b64decode
from collections.abc import AsyncGenerator
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET


# Also called TrickyBox
class FixIntegrity(Downloader):
    # https://t.me/s/randommodules
    # https://github.com/GueRapii/FixIntegrity
    # https://github.com/GueRapii/TrickBox
    URL = 'github:GueRapii/randommodulesfiles::file.enc'

    async def get_keybox(self) -> AsyncGenerator[Element | None]:
        self.logger.info('Downloading encoded keybox')
        self.encoded = str(await anext(self.download_urls()))

        yield ET.fromstring(self.decode_keybox())

    def decode_keybox(self) -> str:
        return b64decode(self.encoded).decode('ascii')
