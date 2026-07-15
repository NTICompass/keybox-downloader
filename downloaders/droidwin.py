from . import Downloader
from bs4 import BeautifulSoup
from collections.abc import AsyncGenerator, Callable
from io import BytesIO
from program.keybox import Keybox
from typing import final, override
import re
import zipfile


@final
class DroidWin(Downloader):
    DESCRIPTION = 'Droidwin Keybox Module'
    URL = (
        'https://droidwin.com/droidwin-keybox-module-gives-you-a-new-unrevoked-keybox/'
    )

    @override
    def __init__(self):
        super().__init__()
        self.cloudflare = False

    @override
    async def process(
        self, downloaded: AsyncGenerator[str]
    ) -> AsyncGenerator[Keybox | None]:
        self.logger.info('Downloading webpage')
        html = await self.do_download(
            lambda: (
                downloaded
                if not self.cloudflare
                else self.download_urls(cloudflare=True)
            )
        )

        soup = BeautifulSoup(html, 'html.parser')
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
            zip_dl = await self.do_download(
                lambda: self.download_urls(
                    binary=True,
                    cloudflare=self.cloudflare,
                    download=(str(link.attrs['href']),),
                ),
                True,
            )

            yield self.unzip_keybox(zip_dl)

    async def do_download[T: str | bytes](
        self, dl: Callable[[], AsyncGenerator[T]], force_zip=False
    ) -> T:
        gen = dl()

        try:
            data = await anext(gen)

            if (
                force_zip
                and not zipfile.is_zipfile(BytesIO(data))
                and not self.cloudflare
            ):
                """
                This means that the httpx returned the CloudFlare challenge page via a 200!
                """
                self.logger.info('Failed to download zip, retrying with CloudScraper')

                self.cloudflare = True
                await gen.aclose()
                gen = dl()

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

        return data

    @override
    def decode(self, encoded: str) -> str:
        raise NotImplementedError('Keybox not encoded')
