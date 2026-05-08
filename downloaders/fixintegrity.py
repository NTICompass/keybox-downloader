from . import Downloader
from base64 import b64decode


# Also called TrickyBox
class FixIntegrity(Downloader):
    # https://t.me/s/randommodules
    # https://github.com/GueRapii/FixIntegrity
    # https://github.com/GueRapii/TrickBox
    URL = 'github:GueRapii/randommodulesfiles::file.enc'

    def decode_keybox(self, encoded: str) -> str:
        return b64decode(encoded).decode('ascii')
