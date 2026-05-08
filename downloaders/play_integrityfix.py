from . import Downloader
from collections.abc import AsyncGenerator
from dotenv import load_dotenv
from typing import final, override, TypedDict
from xml.etree.ElementTree import Element
import json
import os


# https://docs.github.com/en/rest/releases/releases?apiVersion=2026-03-10
class GitHubAsset(TypedDict):
    name: str
    digest: str
    content_type: str
    browser_download_url: str


class GitHubRelease(TypedDict):
    assets: list[GitHubAsset]


# Root Phantom Fateh
@final
class PlayIntegrityFix(Downloader):
    # https://t.me/s/kernelsu1
    # Found via: https://t.me/s/keybox_xml
    # https://github.com/FBIVIP/Play-IntegrityFix/releases
    URL = 'https://api.github.com/repos/FBIVIP/Play-IntegrityFix/releases/latest'

    @override
    def __init__(self):
        super().__init__()
        load_dotenv()

        github_token = os.getenv('GITHUB_TOKEN')

        if github_token:
            self.extra_headers = {'Authorization': f'Bearer {github_token}'}

    @override
    async def process(
        self, downloaded: AsyncGenerator[str]
    ) -> AsyncGenerator[Element | None]:
        self.logger.info('Searching for latest release')

        releases: GitHubRelease = json.loads(await anext(downloaded))
        self.extra_headers = None

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

                yield self.unzip(zip_dl, 'zygisk/.@fateh7')

    @override
    def decode(self, encoded: str) -> str:
        raise NotImplementedError('Keybox not encoded')
