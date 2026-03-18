from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from httpx import AsyncClient, Response, URL
from xml.etree.ElementTree import Element
import asyncio
import logging


def fix_rsa_keys(key_xml: Element | None) -> Element | None:
    if key_xml is None:
        return None

    not_rsa = ('xlp', 'nbs')

    for algo in not_rsa:
        try:
            key_xml.find(f'.//Key[@algorithm="{algo}"]').set('algorithm', 'rsa')
            break
        except AttributeError:
            continue

    return key_xml


def build_github_url(repo: str, branch: str, file: str) -> str:
    return f'https://raw.githubusercontent.com/{repo}/refs/heads/{branch if len(branch) > 0 else "main"}/{file}'


class Downloader(ABC):
    URL: str
    URLS: list[str]
    client = AsyncClient(
        http2=True,
        follow_redirects=True,
        timeout=None,
        headers={
            'Accept-Encoding': 'br, gzip',
            'Cache-Control': 'no-cache',
        },
    )

    def __init__(self):
        self.encoded: str | None = None
        self.current_url: URL | None = None
        self.logger = logging.getLogger(type(self).__name__)

    @abstractmethod
    def get_keybox(self) -> AsyncGenerator[Element | None]:
        pass

    @abstractmethod
    def decode_keybox(self) -> str:
        pass

    async def download_all(self, *download: str) -> AsyncGenerator[Response]:
        """
        `yield from` doesn't work in `AsyncGenerator`
        https://peps.python.org/pep-0525/#asynchronous-yield-from
        """
        for r in await asyncio.gather(
            *[
                self.client.get(
                    build_github_url(*dl.split(':', 4)[1:])
                    if dl.startswith('github:')
                    else dl
                )
                for dl in download
            ]
        ):
            yield r

    async def download_urls(self, binary: bool = False) -> AsyncGenerator[str | bytes]:
        try:
            download = self.URLS
        except AttributeError:
            download = (self.URL,)

        async for r in self.download_all(*download):
            self.current_url = r.url
            yield r.content if binary else r.text
