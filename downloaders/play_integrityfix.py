from . import Downloader
from io import BytesIO
from typing import AsyncGenerator
from xml.etree.ElementTree import Element
from zipfile import ZipFile
import json
import xml.etree.ElementTree as ET


# Root Phantom Fateh
class PlayIntegrityFix(Downloader):
    # https://t.me/s/kernelsu1
    # Found via: https://t.me/s/keybox_xml
    # https://github.com/FBIVIP/Play-IntegrityFix/releases
    URL = 'https://api.github.com/repos/FBIVIP/Play-IntegrityFix/releases/latest'

    async def get_keybox(self) -> AsyncGenerator[Element | None]:
        self.logger.info('Searching for latest release')
        releases = json.loads(await anext(self.download_urls()))

        if releases['assets']:
            for release in releases['assets']:
                self.logger.info(f'Downloading {release["name"]}')

                # hash = release['digest']
                zip_dl = await anext(
                    self.download_urls(
                        binary=True,
                        download=(release['browser_download_url'],),
                    )
                )

                with ZipFile(BytesIO(zip_dl), 'r') as zip_file:
                    self.logger.info('Extracting keybox from ZIP file')
                    with zip_file.open('zygisk/.@fateh7') as keybox_data:
                        yield ET.parse(keybox_data).getroot()

    def decode_keybox(self) -> str:
        pass
