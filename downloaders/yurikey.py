from base64 import b64decode
from downloaders.downloader import Downloader
from utils.shellvar import get_var_from_shell
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET


class YuriKey(Downloader):
    # https://t.me/s/yuriiroot
    URL = 'https://github.com/YurikeyDev/yurikey/raw/refs/heads/main/conf'

    async def get_keybox(self) -> Element:
        self.encoded = await self.get_encoded_keybox()
        self.logger.info('Decoding keybox xml')

        key_xml = ET.fromstring(self.decode_keybox())

        try:
            # Change `<Key algorithm="nbs">` to `<Key algorithm="rsa">`
            key_xml.find('.//Key[@algorithm="nbs"]').set('algorithm', 'rsa')
        except AttributeError:
            pass

        return key_xml

    async def get_encoded_keybox(self) -> str:
        self.logger.info('Downloading encoded keybox')

        keybox_script = b64decode(await anext(self.download_urls())).decode('utf-8')
        keybox_vars = get_var_from_shell(keybox_script, ['KEYBOX_BASE64_PAYLOAD'])
        return keybox_vars['KEYBOX_BASE64_PAYLOAD']

    def decode_keybox(self) -> str:
        return b64decode(self.encoded).decode('ascii')
