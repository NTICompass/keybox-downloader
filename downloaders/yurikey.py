from base64 import b64decode
from downloaders.downloader import Downloader
from io import BytesIO
from xml.etree.ElementTree import Element
import binary2strings as b2s
import xml.etree.ElementTree as ET


class YuriKey(Downloader):
    # This has been changed to an ELF binary
    URL = 'https://github.com/YurikeyDev/yurikey/raw/refs/heads/main/conf'

    async def get_keybox(self) -> Element:
        self.encoded = await self.get_encoded_keybox()
        self.logger.info('Decoding keybox xml')

        return ET.fromstring(self.decode_keybox())

    async def get_encoded_keybox(self) -> str | None:
        self.logger.info('Downloading keybox binary')

        bin_elf = BytesIO(await anext(self.download_urls(True)))
        for string, encoding, span, is_interesting in b2s.extract_all_strings(bin_elf.read(), min_chars=1024):
           if is_interesting:
               return string
        return None

    def decode_keybox(self) -> str:
        return b64decode(self.encoded).decode('ascii')