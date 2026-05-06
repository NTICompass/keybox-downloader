from . import Downloader
from io import BytesIO
from typing import AsyncGenerator, TypedDict
from xml.etree.ElementTree import Element
from zipfile import ZipFile
import json
import xml.etree.ElementTree as ET


# https://docs.github.com/en/rest/releases/releases?apiVersion=2026-03-10
class GitHubAsset(TypedDict):
    name: str
    digest: str
    content_type: str
    browser_download_url: str


class GitHubRelease(TypedDict):
    assets: list[GitHubAsset]


# Root Phantom Fateh
class PlayIntegrityFix(Downloader):
    # https://t.me/s/kernelsu1
    # Found via: https://t.me/s/keybox_xml
    # https://github.com/FBIVIP/Play-IntegrityFix/releases
    URL = 'https://api.github.com/repos/FBIVIP/Play-IntegrityFix/releases/latest'

    async def get_keybox(self) -> AsyncGenerator[Element | None]:
        self.logger.info('Searching for latest release')
        releases: GitHubRelease = json.loads(await anext(self.download_urls()))

        for release in releases['assets']:
            if release['content_type'] == 'application/zip':
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
        raise NotImplementedError('Keybox not encoded')
