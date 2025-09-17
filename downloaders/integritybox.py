from base64 import b64decode
from codecs import decode
from downloaders.downloader import Downloader
from utils.shellvar import get_var_from_shell
import requests


class IntegrityBox(Downloader):
    URL='https://github.com/MeowDump/Integrity-Box/raw/refs/heads/main/webroot/common_scripts/key.sh'

    def get_keybox(self) -> str:
        self.encoded = requests.get(self.__get_keybox_url()).text
        return self.__decode_keybox()

    def __get_keybox_url(self) -> str:
        keybox_script = requests.get(self.URL).text
        keybox_vars = get_var_from_shell(keybox_script, ['I', 'J', 'K', 'LOL'])
        return b64decode(keybox_vars['I'] + keybox_vars['J'] + keybox_vars['K'] + keybox_vars['LOL']).decode('ascii')

    def __decode_keybox(self) -> str:
        encoded = self.encoded

        # Decode base64 ten times!
        for i in range(10) :
            encoded = b64decode(encoded).decode('ascii')

        # Then decode the hex bytes
        encoded = bytes.fromhex(encoded).decode('utf-8')

        # Finally use rot13
        return decode(encoded, 'rot_13')