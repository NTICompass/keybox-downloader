from abc import ABC, abstractmethod
from httpx import AsyncClient
from typing import AsyncGenerator, Generator, Optional
from xml.etree.ElementTree import Element
import logging


class Downloader(ABC):
    URL: str
    URLS: list[str]
    client: AsyncClient = AsyncClient(follow_redirects=True)

    def __init__(self):
        self.encoded: Optional[str] = None
        self.current_url: Optional[str] = None
        self.logger = logging.getLogger(type(self).__name__)

    @abstractmethod
    async def get_keybox(self) -> Element | Generator[Element]:
        pass

    @abstractmethod
    def decode_keybox(self) -> str:
        pass

    async def download_urls(self, binary: bool = False) -> AsyncGenerator[str | bytes]:
        try:
            download = self.URLS
        except AttributeError:
            download = (self.URL,)

        for dl in download:
            self.current_url = dl
            r = await self.client.get(dl)
            yield r.content if binary else r.text