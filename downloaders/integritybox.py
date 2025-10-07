from base64 import b64decode
from codecs import decode
from downloaders.downloader import Downloader
from utils.shellvar import get_var_from_shell
from xml.etree.ElementTree import Element
import re
import xml.etree.ElementTree as ET

"""
https://integritybox.vercel.app/
https://github.com/freekeybox/mona/
https://github.com/freekeybox/mona/raw/refs/heads/main/meow.tar
"""


class IntegrityBox(Downloader):
    URL = 'https://github.com/MeowDump/Integrity-Box/raw/refs/heads/main/webroot/common_scripts/key.sh'
    FIX_URL = 'https://github.com/MeowDump/Integrity-Box/raw/refs/heads/main/webroot/common_scripts/cleanup.sh'

    def __init__(self):
        super().__init__()

        self.junk: list[str] | set[str] | None = None

    async def get_keybox(self) -> Element:
        download_url = await self.get_keybox_url()
        junk_vars = get_var_from_shell((await self.client.get(self.FIX_URL)).text, ['X'])

        self.junk = junk_vars['X'].split(',')
        self.encoded = (await self.client.get(download_url)).text

        # parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        return ET.fromstring(self.decode_keybox())

    async def get_keybox_url(self) -> str:
        self.logger.info('Downloading keybox script')

        keybox_script = await anext(self.download_urls())
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
