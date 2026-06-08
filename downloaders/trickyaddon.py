from . import Downloader
from base64 import b64decode
from typing import final, override


@final
class TrickyAddon(Downloader):
    # https://t.me/s/kowchannel
    DESCRIPTION = 'Tricky Addon - Update Target List module (KOWX712 @ GitHub)'
    URL = 'github:KOWX712/Tricky-Addon-Update-Target-List:keybox:.extra'

    @override
    def decode(self, encoded: str) -> str:
        self.logger.info('Decoding keybox xml')

        # First decode the hex bytes
        encoded = bytes.fromhex(encoded).decode('ascii')

        # Then base64 decode
        return b64decode(encoded).decode('ascii')
