from . import Downloader
from base64 import b64decode
from typing import final, override


@final
class YuriKey(Downloader):
    # https://t.me/s/yuriiroot
    # https://t.me/s/yuriservice
    URL = 'github:Yurii0307/yurikey::key'

    @override
    def decode(self, encoded: str) -> str:
        return b64decode(encoded).decode('ascii')
