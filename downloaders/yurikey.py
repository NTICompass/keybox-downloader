from base64 import b64decode
from downloaders.downloader import Downloader
from utils.shellvar import get_var_from_shell
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET


class YuriKey(Downloader):
    URL = 'https://github.com/YurikeyDev/yurikey/raw/refs/heads/main/conf'

    async def get_keybox(self) -> Element:
        self.encoded = self.get_encoded_keybox()
        self.logger.info('Decoding keybox xml')

        return ET.fromstring(self.decode_keybox())

    def get_encoded_keybox(self) -> str:
        self.logger.info('Downloading encoded keybox')

        keybox_script = b64decode(next(self.download_urls())).decode('utf-8')
        keybox_vars = get_var_from_shell(keybox_script, ['KEYBOX_BASE64_PAYLOAD'])
        return keybox_vars['KEYBOX_BASE64_PAYLOAD']

    def decode_keybox(self) -> str:
        return b64decode(self.encoded).decode('ascii')