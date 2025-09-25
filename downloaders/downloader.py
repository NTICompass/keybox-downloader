from abc import ABC, abstractmethod
from requests import Session
from typing import Generator, Optional
from xml.etree.ElementTree import Element
import logging


class Downloader(ABC):
    URL: str
    URLS: list[str]

    def __init__(self):
        self.encoded: Optional[str] = None
        self.current_url: Optional[str] = None
        self.logger = logging.getLogger(type(self).__name__)
        self.dl = Session()

    @abstractmethod
    def get_keybox(self) -> Element | Generator[Element]:
        pass

    @abstractmethod
    def decode_keybox(self) -> str:
        pass

    def download_urls(self) -> Generator[str]:
        try:
            download = self.URLS
        except AttributeError:
            download = (self.URL,)

        for dl in download:
            self.current_url = dl
            yield self.dl.get(dl).text