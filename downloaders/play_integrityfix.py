# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""PlayIntegrityFix download module."""

from typing import TYPE_CHECKING, final, override

from . import Downloader

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from program.keybox import Keybox


# Root Phantom Fateh (@fateh7)
@final
class PlayIntegrityFix(Downloader, enabled=False):
    """PlayIntegrityFix Downloader.

    Module found via: https://t.me/s/keybox_xml

    Telegram:
    https://t.me/ProfessorRoot_DZ
    https://t.me/s/kernelsu1

    GitHub:
    https://github.com/FBIVIP/Play-IntegrityFix/releases
    """

    DESCRIPTION = 'PlayIntegrity module (FBIVIP @ GitHub, aka "Root Phantom Fateh", aka @fateh7)'
    URL = 'github-api:FBIVIP/Play-IntegrityFix'

    @override
    def __init__(self) -> None:
        super().__init__()

        self.extra_headers = Downloader.get_github_token()

    @override
    async def process(self, downloaded: AsyncGenerator[str]) -> AsyncGenerator[Keybox | None]:
        zip_dl = await self.get_latest_github_release(await anext(downloaded))
        yield self.unzip_keybox(zip_dl) if zip_dl is not None else None

    @override
    def decode(self, encoded: str) -> str:
        msg = 'Keybox not encoded'
        raise NotImplementedError(msg)
