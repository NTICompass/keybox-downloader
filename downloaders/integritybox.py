from base64 import b64decode
from codecs import decode
from downloaders.downloader import Downloader
from utils.shellvar import get_var_from_shell
from xml.etree.ElementTree import Element
import re
import requests
import xml.etree.ElementTree as ET


class IntegrityBox(Downloader):
    URL='https://github.com/MeowDump/Integrity-Box/raw/refs/heads/main/webroot/common_scripts/key.sh'
    FIX_URL='https://github.com/MeowDump/Integrity-Box/raw/refs/heads/main/cleanup.sh'

    def __init__(self):
        super().__init__()

        junk_vars = get_var_from_shell(requests.get(self.FIX_URL).text, ['X'])
        self.junk: list[str] = junk_vars['X'].split(',')

    def get_keybox(self) -> Element:
        self.encoded = requests.get(self.__get_keybox_url()).text
        return ET.fromstring(self.__decode_keybox())

    def __get_keybox_url(self) -> str:
        self.logger.info('Downloading keybox script')

        keybox_script = requests.get(self.URL).text
        keybox_vars = get_var_from_shell(keybox_script, ['I', 'J', 'K', 'LOL'])
        return b64decode(keybox_vars['I'] + keybox_vars['J'] + keybox_vars['K'] + keybox_vars['LOL']).decode('ascii')

    def __decode_keybox(self) -> str:
        self.logger.info('Decoding keybox xml')

        encoded = self.encoded

        # Decode base64 ten times!
        for i in range(10) :
            encoded = b64decode(encoded).decode('ascii')

        # Then decode the hex bytes
        encoded = bytes.fromhex(encoded).decode('utf-8')

        # Next use rot13
        encoded = decode(encoded, 'rot_13')

        # Finally remove extra "junk" from the file
        return re.sub(r'({})'.format('|'.join(self.junk)), '', encoded)