from . import Downloader, fix_rsa_keys
from base64 import b64decode
from utils.shellvar import get_var_from_shell
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET


class YuriKey(Downloader):
    # https://t.me/s/yuriiroot
    URL = 'https://github.com/Yurii0307/yurikey/raw/refs/heads/main/conf'

    async def get_keybox(self) -> Element:
        self.logger.info('Decoding keybox xml')
        self.encoded = await self.get_encoded_keybox()

        return fix_rsa_keys(ET.fromstring(self.decode_keybox()))

    async def get_encoded_keybox(self) -> str:
        self.logger.info('Downloading encoded keybox')

        keybox_script = b64decode(await anext(self.download_urls())).decode('utf-8')
        keybox_vars = get_var_from_shell(keybox_script, ['KEYBOX_BASE64_PAYLOAD'])
        return keybox_vars['KEYBOX_BASE64_PAYLOAD']

    def decode_keybox(self) -> str:
        encoded = self.encoded

        # Decode base64 twice
        for i in range(2):
            encoded = b64decode(encoded).decode('ascii')

        return encoded
