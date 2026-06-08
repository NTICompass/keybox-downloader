from . import Downloader
from base64 import b64decode
from typing import final, override


@final
class TrickyAddon(Downloader):
    # https://t.me/s/kowchannel
    URL = 'github:KOWX712/Tricky-Addon-Update-Target-List:keybox:.extra'

    @property
    @override
    def description(self) -> str:
        return 'Tricky Addon - Update Target List module (KOWX712 @ GitHub)'

    @override
    def decode(self, encoded: str) -> str:
        self.logger.info('Decoding keybox xml')

        # First decode the hex bytes
        encoded = bytes.fromhex(encoded).decode('ascii')

        # Then base64 decode
        return b64decode(encoded).decode('ascii')
