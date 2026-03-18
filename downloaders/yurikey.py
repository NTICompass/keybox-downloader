from . import Downloader
from base64 import b64decode
from collections.abc import AsyncGenerator
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET


class YuriKey(Downloader):
    # https://t.me/s/yuriiroot
    URL = 'github:Yurii0307/yurikey::key'

    async def get_keybox(self) -> AsyncGenerator[Element | None]:
        self.logger.info('Downloading encoded keybox')
        self.encoded = await anext(self.download_urls())

        yield ET.fromstring(self.decode_keybox())

    def decode_keybox(self) -> str:
        return b64decode(self.encoded).decode('ascii')
