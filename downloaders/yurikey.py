from . import Downloader, fix_rsa_keys
from base64 import b64decode
from collections.abc import AsyncGenerator
from utils.shellvar import get_var_from_shell
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET


class YuriKey(Downloader):
    # https://t.me/s/yuriiroot
    URL = 'https://github.com/Yurii0307/yurikey/raw/refs/heads/main/key'

    async def get_keybox(self) -> AsyncGenerator[Element]:
        self.logger.info('Downloading encoded keybox')
        self.encoded = await anext(self.download_urls())

        yield ET.fromstring(self.decode_keybox())

    def decode_keybox(self) -> str:
        return b64decode(self.encoded).decode('ascii')
