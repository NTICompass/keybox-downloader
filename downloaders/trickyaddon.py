from . import Downloader
from base64 import b64decode
from collections.abc import AsyncGenerator
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET


class TrickyAddon(Downloader):
    # https://t.me/s/kowchannel
    URL = 'github:KOWX712/Tricky-Addon-Update-Target-List:keybox:.extra'

    def decode_keybox(self, encoded: str) -> str:
        self.logger.info('Decoding keybox xml')

        # First decode the hex bytes
        encoded = bytes.fromhex(encoded).decode('ascii')

        # Then base64 decode
        return b64decode(encoded).decode('ascii')
