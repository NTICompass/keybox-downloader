from downloaders.downloader import Downloader
from base64 import b64decode
from utils.shellvar import get_var_from_shell
import requests


class YuriKey(Downloader):
    URL='https://github.com/YurikeyDev/yurikey/raw/refs/heads/main/conf'

    def get_keybox(self) -> str:
        self.encoded = self.__get_encoded_keybox()
        return b64decode(self.encoded).decode('ascii')

    def __get_encoded_keybox(self) -> str:
        keybox_script = b64decode(requests.get(self.URL).text).decode('utf-8')
        keybox_vars = get_var_from_shell(keybox_script, ['KEYBOX_BASE64_PAYLOAD'])
        return keybox_vars['KEYBOX_BASE64_PAYLOAD']