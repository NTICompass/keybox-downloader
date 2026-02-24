from . import Downloader
from base64 import b64decode
from bs4 import BeautifulSoup
from collections.abc import AsyncGenerator
from io import BytesIO
from xml.etree.ElementTree import Element, ParseError
from zipfile import ZipFile
import xml.etree.ElementTree as ET


class YuriKey(Downloader):
    # https://t.me/s/yuriiroot
    URL = 'https://github.com/Yurii0307/yurikey/raw/refs/heads/main/key'

    async def get_keybox(self) -> AsyncGenerator[Element | None]:
        self.logger.info('Downloading encoded keybox')
        self.encoded = await anext(self.download_urls())

        data = self.decode_keybox()
        try:
            yield ET.fromstring(data)
        except ParseError:
            # We might have an HTML file from "filebin.net"
            # https://filebin.net/api
            self.logger.info('XML parsing failed, assuming filebin HTML')
            soup = BeautifulSoup(data, 'html.parser')

            for code in soup.find_all('code'):
                self.logger.info('Downloading ZIP from filebin.net')
                url = f'https://filebin.net/archive/{code.get_text()}/zip'
                zip_data = (
                    await self.client.get(url, headers={'User-Agent': 'curl/8.18.0'})
                ).content

                with ZipFile(BytesIO(zip_data), 'r') as zip_file:
                    self.logger.info('Unzipping data...')
                    for name in zip_file.namelist():
                        with zip_file.open(name) as keybox_data:
                            yield ET.fromstring(keybox_data.read())

    def decode_keybox(self) -> str:
        return b64decode(self.encoded).decode('ascii')
