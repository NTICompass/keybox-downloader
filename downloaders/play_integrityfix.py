from . import Downloader
from collections.abc import AsyncGenerator
from dotenv import load_dotenv
from pathlib import Path
from program.keybox import Keybox
from typing import final, override, TypedDict, ClassVar
import __main__
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


# Root Phantom Fateh (@fateh7)
@final
class PlayIntegrityFix(Downloader):
    ENABLED = False

    # https://t.me/ProfessorRoot_DZ
    # https://t.me/s/kernelsu1
    # Found via: https://t.me/s/keybox_xml
    # https://github.com/FBIVIP/Play-IntegrityFix/releases
    DESCRIPTION = (
        'PlayIntegrity module (FBIVIP @ GitHub, aka "Root Phantom Fateh", aka @fateh7)'
    )
    URL = 'https://api.github.com/repos/FBIVIP/Play-IntegrityFix/releases/latest'

    env_file: ClassVar[Path] = __main__.exe_root / '.env'

    @override
    def __init__(self):
        super().__init__()
        load_dotenv(self.env_file if self.env_file.exists() else None)

        github_token = os.getenv('GITHUB_TOKEN')

        if github_token:
            self.extra_headers = {'Authorization': f'Bearer {github_token}'}

    @override
    async def process(
        self, downloaded: AsyncGenerator[str]
    ) -> AsyncGenerator[Keybox | None]:
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

                yield self.unzip(zip_dl, 'keybox.xml')

    @override
    def decode(self, encoded: str) -> str:
        raise NotImplementedError('Keybox not encoded')
