from abc import ABC, abstractmethod
from typing import Generator, Optional, Union
from xml.etree.ElementTree import Element
import logging
import requests


class Downloader(ABC):
    URL: str
    URLS: list[str]

    def __init__(self):
        self.encoded: Optional[str] = None
        self.current_url: Optional[str] = None
        self.logger = logging.getLogger(type(self).__name__)

    @abstractmethod
    def get_keybox(self) -> Union[Element, Generator[Element]]:
        pass

    def download_urls(self) -> Generator[str]:
        try:
            download = self.URLS
        except AttributeError:
            download = (self.URL,)

        for dl in download:
            self.current_url = dl
            yield requests.get(dl).text