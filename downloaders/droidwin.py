# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Droidwin.com download module."""

import re
import zipfile
from functools import partial
from io import BytesIO
from typing import TYPE_CHECKING, final, override

from bs4 import BeautifulSoup

from . import Downloader

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from bs4 import Tag

    from program.keybox import Keybox


@final
class DroidWin(Downloader):
    """Droidwin Keybox Module Downloader.

    Main Page:
    https://droidwin.com/
    """

    DESCRIPTION = 'Droidwin Keybox Module'
    URL = 'https://droidwin.com/droidwin-keybox-module-gives-you-a-new-unrevoked-keybox/'

    @override
    def __init__(self) -> None:
        super().__init__()
        self.cloudflare = False

    @override
    async def process(self, downloaded: AsyncGenerator[str]) -> AsyncGenerator[Keybox | None]:
        self.logger.info('Downloading webpage')
        html = await self.do_download(
            lambda: downloaded if not self.cloudflare else self.download_urls(cloudflare=True)
        )

        if html is not None:
            soup = BeautifulSoup(html, 'html.parser')
            links = soup.find_all(
                'a', {'href': re.compile(r'^https://droidwin.com/wp-content/.+/droidwin-keybox-.+\.zip')}
            )

            def link_dl(curr_link: Tag) -> AsyncGenerator[bytes]:
                """Create a generator to download the `href` from the specified `<a />` tag.

                Args:
                    curr_link: The `<a />` element

                Returns:
                    An `AsyncGenerator` yielding `bytes`

                """
                return self.download_urls(
                    binary=True, cloudflare=self.cloudflare, download=[str(curr_link.attrs['href'])]
                )

            for link in links:
                self.logger.info('Downloading module ZIP file')
                zip_dl = await self.do_download(partial(link_dl, link), force_zip=True)

                yield self.unzip_keybox(zip_dl) if zip_dl is not None else None

    async def do_download[T: str | bytes](
        self, dl: partial[AsyncGenerator[T]] | Callable[[], AsyncGenerator[T]], *, force_zip: bool = False
    ) -> T | None:
        """Download the webpage and module.zip from Droidwin.com.

        Args:
            dl: `lambda` function returning an `AsyncGenerator` yielding the webpage or zip file
            force_zip: Ensure the downloaded file is a zip file

        Returns:
            `str`, `bytes`, or `None`

        """
        gen = dl()

        try:
            data = await anext(gen)
        except StopAsyncIteration:
            """
            This means that the httpx returned an error downloading the website
            Probably a 403, probably a CloudFlare challenge...
            """
            self.logger.info('Hit CloudFlare challenge, trying to solve it')

            self.cloudflare = True
            await gen.aclose()
            gen = dl()

            data = await anext(gen)
        finally:
            await gen.aclose()

        # TODO: Sometimes the solver fails and returns the challenge HTML (on Android)  # ruff: ignore[line-contains-todo]
        if force_zip and not zipfile.is_zipfile(BytesIO(data)):
            return None

        return data

    @override
    def decode(self, encoded: str) -> str:
        msg = 'Keybox not encoded'
        raise NotImplementedError(msg)
