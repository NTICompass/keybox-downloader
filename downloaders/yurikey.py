from base64 import b64decode
from downloaders.downloader import Downloader
from utils.shellvar import get_var_from_shell
from xml.etree.ElementTree import Element
import requests
import xml.etree.ElementTree as ET


class YuriKey(Downloader):
    URL='https://github.com/YurikeyDev/yurikey/raw/refs/heads/main/conf'

    def get_keybox(self) -> Element:
        self.encoded = self.__get_encoded_keybox()
        return ET.fromstring(b64decode(self.encoded).decode('ascii'))

    def __get_encoded_keybox(self) -> str:
        keybox_script = b64decode(requests.get(self.URL).text).decode('utf-8')
        keybox_vars = get_var_from_shell(keybox_script, ['KEYBOX_BASE64_PAYLOAD'])
        return keybox_vars['KEYBOX_BASE64_PAYLOAD']