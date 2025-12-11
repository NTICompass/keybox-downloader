from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from httpx import AsyncClient, Response, URL
from xml.etree.ElementTree import Element
import asyncio
import logging


class Downloader(ABC):
    URL: str
    URLS: list[str]
    client: AsyncClient = AsyncClient(follow_redirects=True, timeout=None)

    def __init__(self):
        self.encoded: str | None = None
        self.current_url: URL | None = None
        self.logger = logging.getLogger(type(self).__name__)

    @abstractmethod
    async def get_keybox(self) -> Element | None:
        pass

    @abstractmethod
    def decode_keybox(self) -> str:
        pass

    async def download_all(self, *download: str) -> AsyncGenerator[Response]:
        """`yield from` doesn't work in `AsyncGenerator`"""
        for r in await asyncio.gather(*[self.client.get(dl) for dl in download]):
            yield r

    async def download_urls(self, binary: bool = False) -> AsyncGenerator[str | bytes]:
        try:
            download = self.URLS
        except AttributeError:
            download = (self.URL,)

        async for r in self.download_all(*download):
            self.current_url = r.url
            yield r.content if binary else r.text
