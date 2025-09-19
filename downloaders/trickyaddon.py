from base64 import b64decode
from downloaders.downloader import Downloader
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET


class TrickyAddon(Downloader):
    URL='https://github.com/KOWX712/Tricky-Addon-Update-Target-List/raw/refs/heads/main/.extra'

    def get_keybox(self) -> Element:
        self.logger.info('Downloading encoded keybox')

        self.encoded = next(self.download_urls())
        return ET.fromstring(self.__decode_keybox())

    def __decode_keybox(self) -> str:
        self.logger.info('Decoding keybox xml')

        encoded = self.encoded

        # First decode the hex bytes
        encoded = bytes.fromhex(encoded).decode('ascii')

        # Then base64 decode
        return b64decode(encoded).decode('ascii')