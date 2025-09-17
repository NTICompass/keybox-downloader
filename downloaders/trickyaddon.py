from downloaders.downloader import Downloader
from base64 import b64decode
import requests


class TrickyAddon(Downloader):
    URL='https://github.com/KOWX712/Tricky-Addon-Update-Target-List/raw/refs/heads/main/.extra'

    def get_keybox(self) -> str:
        self.encoded = requests.get(self.URL).text
        return self.__decode_keybox()

    def __decode_keybox(self) -> str:
        encoded = self.encoded

        # First decode the hex bytes
        encoded = bytes.fromhex(encoded).decode('ascii')

        # Then base64 decode
        return b64decode(encoded).decode('ascii')