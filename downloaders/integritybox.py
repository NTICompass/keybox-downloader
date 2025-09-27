from base64 import b64decode
from codecs import decode
from downloaders.downloader import Downloader
from utils.shellvar import get_var_from_shell
from xml.etree.ElementTree import Element
import re
import xml.etree.ElementTree as ET


class IntegrityBox(Downloader):
    # https://github.com/MeowDump/MeowDump/raw/refs/heads/main/NullVoid/Arrival.tar
    URL = 'https://github.com/MeowDump/Integrity-Box/raw/refs/heads/main/webroot/common_scripts/key.sh'
    FIX_URL = 'https://github.com/MeowDump/Integrity-Box/raw/refs/heads/main/webroot/common_scripts/cleanup.sh'

    def __init__(self):
        super().__init__()

        junk_vars = get_var_from_shell(self.dl.get(self.FIX_URL).text, ['X'])
        self.junk: list[str] = junk_vars['X'].split(',')

    async def get_keybox(self) -> Element:
        self.encoded = self.dl.get(self.get_keybox_url()).text
        return ET.fromstring(self.decode_keybox())

    def get_keybox_url(self) -> str:
        self.logger.info('Downloading keybox script')

        keybox_script = next(self.download_urls())
        keybox_vars = get_var_from_shell(keybox_script, ['I', 'J', 'K', 'LOL'])
        return b64decode(keybox_vars['I'] + keybox_vars['J'] + keybox_vars['K'] + keybox_vars['LOL']).decode('ascii')

    def decode_keybox(self) -> str:
        self.logger.info('Decoding keybox xml')

        encoded = self.encoded

        # Decode base64 ten times!
        for i in range(10):
            encoded = b64decode(encoded).decode('ascii')

        # Then decode the hex bytes
        encoded = bytes.fromhex(encoded).decode('utf-8')

        # Next use rot13
        encoded = decode(encoded, 'rot_13')

        # Finally remove extra "junk" from the file
        return re.sub(rf'({'|'.join(self.junk)})', '', encoded)