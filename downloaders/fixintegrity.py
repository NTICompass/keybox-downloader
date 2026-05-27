from . import Downloader
from base64 import b64decode
from typing import final, override


# Also called TrickyBox
@final
class FixIntegrity(Downloader):
    # https://t.me/s/randommodules
    # https://github.com/GueRapii/FixIntegrity
    # https://github.com/GueRapii/TrickBox
    # https://t.me/s/CollectionByCharlie
    URL = 'github:GueRapii/randommodulesfiles::file.enc'

    @override
    def decode(self, encoded: str) -> str:
        return b64decode(encoded).decode('ascii')
