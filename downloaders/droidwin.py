from . import Downloader
from bs4 import BeautifulSoup
from collections.abc import AsyncGenerator
from typing import final, override
from xml.etree.ElementTree import Element
import re


@final
class DroidWin(Downloader):
    URL = (
        'https://droidwin.com/droidwin-keybox-module-gives-you-a-new-unrevoked-keybox/'
    )

    @override
    async def process(
        self, downloaded: AsyncGenerator[str]
    ) -> AsyncGenerator[Element | None]:
        self.logger.info('Downloading webpage')

        cloudflare = False

        try:
            html = await anext(downloaded)
        except StopAsyncIteration:
            """
            This means that the httpx returned an error downloading the website
            Probably a 403, probably a CloudFlare challenge...
            """
            self.logger.info('Hit CloudFlare challenge, trying to solve it')

            cloudflare = True
            html = await anext(self.download_urls(cloudflare=True))

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
            zip_dl = await anext(
                self.download_urls(
                    binary=True,
                    cloudflare=cloudflare,
                    download=(str(link.attrs['href']),),
                )
            )

            yield self.unzip(zip_dl, 'keybox.xml')

    @override
    def decode(self, encoded: str) -> str:
        raise NotImplementedError('Keybox not encoded')
