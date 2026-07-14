from . import Downloader
from base64 import b64decode
from typing import final, override


@final
class AlwaysStrong(Downloader):
    # https://t.me/s/keyboxstrong
    # https://t.me/evokeroot
    # https://t.me/evokerr
    # https://github.com/evoker0/AlwaysStrong
    DESCRIPTION = 'AlwaysStrong module (evoker0 @ GitHub)'
    URL = 'https://evoker.qzz.io/key'

    extra_headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android) asfetch/1.0'}

    @override
    def decode(self, encoded: str) -> str:
        return b64decode(encoded).decode('ascii')
