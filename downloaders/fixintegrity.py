from base64 import b64decode
from typing import final, override

from . import Downloader


# Also called TrickyBox/TrickBox
@final
class FixIntegrity(Downloader):
    # https://t.me/s/randommodules
    # https://github.com/GueRapii/FixIntegrity
    # https://github.com/GueRapii/TrickBox
    # https://t.me/s/CollectionByCharlie
    DESCRIPTION = 'FixIntegrity or TrickBox module (GueRapii @ GitHub)'
    URL = 'github:GueRapii/randommodulesfiles::file.enc'

    @override
    def decode(self, encoded: str) -> str:
        return b64decode(encoded).decode('ascii')
