from . import Downloader
from collections.abc import AsyncGenerator
from program.keybox import Keybox
from typing import final, override


# Root Phantom Fateh (@fateh7)
@final
class PlayIntegrityFix(Downloader, enabled=False):
    # https://t.me/ProfessorRoot_DZ
    # https://t.me/s/kernelsu1
    # Found via: https://t.me/s/keybox_xml
    # https://github.com/FBIVIP/Play-IntegrityFix/releases
    DESCRIPTION = (
        'PlayIntegrity module (FBIVIP @ GitHub, aka "Root Phantom Fateh", aka @fateh7)'
    )
    URL = 'github-api:FBIVIP/Play-IntegrityFix'

    @override
    def __init__(self):
        super().__init__()

        github_token = Downloader.get_github_token()
        if github_token:
            self.extra_headers = {'Authorization': f'Bearer {github_token}'}

    @override
    async def process(
        self, downloaded: AsyncGenerator[str]
    ) -> AsyncGenerator[Keybox | None]:
        zip_dl = await self.get_latest_github_release(await anext(downloaded))
        yield self.unzip_keybox(zip_dl) if zip_dl is not None else None

    @override
    def decode(self, encoded: str) -> str:
        raise NotImplementedError('Keybox not encoded')
