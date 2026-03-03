from . import Downloader
from bs4 import BeautifulSoup
from collections.abc import AsyncGenerator
from io import BytesIO
from xml.etree.ElementTree import Element
from zipfile import ZipFile
import re
import xml.etree.ElementTree as ET


class DroidWin(Downloader):
    URL = (
        'https://droidwin.com/droidwin-keybox-module-gives-you-a-new-unrevoked-keybox/'
    )

    async def get_keybox(self) -> AsyncGenerator[Element | None]:
        self.logger.info('Downloading webpage')
        webpage = await anext(self.download_urls())

        soup = BeautifulSoup(webpage, 'html.parser')
        links = soup.find_all(
            'a',
            {
                'href': re.compile(
                    r'^https://droidwin.com/wp-content/.+/droidwin-keybox-.+\.zip'
                )
            },
        )

        for link in links:
            self.logger.info('Downloading module ZIP file')
            zip_dl = await self.client.get(
                link.attrs['href'], headers={'User-Agent': 'curl/8.18.0'}
            )

            with ZipFile(BytesIO(zip_dl.content), 'r') as zip_file:
                self.logger.info('Extracting keybox from ZIP file')
                with zip_file.open('keybox.xml') as keybox_data:
                    yield ET.parse(keybox_data).getroot()

    def decode_keybox(self) -> str:
        raise NotImplementedError('Keybox not encoded')
