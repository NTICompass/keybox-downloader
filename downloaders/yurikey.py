from base64 import b64decode
from typing import final, override

from . import Downloader


@final
class YuriKey(Downloader):
    # https://t.me/s/yuriiroot
    # https://t.me/s/yuriservice
    DESCRIPTION = 'YuriKey module (Yurii0307 @ GitHub)'
    URL = 'github:Yurii0307/yurikey::key'

    @override
    def decode(self, encoded: str) -> str:
        return b64decode(encoded).decode('ascii')
