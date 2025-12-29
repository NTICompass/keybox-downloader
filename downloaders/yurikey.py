from . import Downloader, fix_rsa_keys
from base64 import b64decode
from collections.abc import AsyncGenerator
from utils.shellvar import get_var_from_shell
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET


class YuriKey(Downloader):
    # https://t.me/s/yuriiroot
    URL = 'https://github.com/Yurii0307/yurikey/raw/refs/heads/main/conf'
    # I don't know if this is used by the module or the key inside the `conf`
    KEY_URL = 'https://github.com/Yurii0307/yurikey/raw/refs/heads/main/key'

    async def get_keybox(self) -> AsyncGenerator[Element]:
        self.logger.info('Decoding keybox xml')
        keyboxes = []

        # Get the `conf` keybox
        self.encoded = await self.get_encoded_keybox()
        keyboxes.append(self.decode_keybox())

        # And the `key` file
        self.encoded = (await self.client.get(self.KEY_URL)).text
        keyboxes.append(self.decode_keybox())

        # Get the keybox from the `conf` file as well as the `key` file
        for idx, keybox in enumerate(keyboxes):
            xml = fix_rsa_keys(ET.fromstring(keybox))

            keybox_id = xml.find('.//Keybox[@DeviceID]')
            keybox_id.set('DeviceID', f'{keybox_id.get("DeviceID")} {idx + 1:d}')

            yield xml

    async def get_encoded_keybox(self) -> str:
        self.logger.info('Downloading encoded keybox')

        keybox_script = b64decode(await anext(self.download_urls())).decode('utf-8')
        keybox_vars = get_var_from_shell(keybox_script, ['KEYBOX_BASE64_PAYLOAD'])
        return keybox_vars['KEYBOX_BASE64_PAYLOAD']

    def decode_keybox(self) -> str:
        encoded = self.encoded

        loops = 0
        max_loops = 10

        # Decode base64 until it's an XML file (the `conf` file had it dual-encoded)
        while True:
            encoded = b64decode(encoded).decode('ascii')

            if encoded.strip().startswith('<?xml'):
                break
            elif ++loops == max_loops:
                raise ValueError('Cannot decode keybox')

        return encoded
