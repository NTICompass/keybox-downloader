from . import Downloader
from base64 import b64decode


class YuriKey(Downloader):
    # https://t.me/s/yuriiroot
    URL = 'github:Yurii0307/yurikey::key'

    def decode_keybox(self, encoded: str) -> str:
        return b64decode(encoded).decode('ascii')
