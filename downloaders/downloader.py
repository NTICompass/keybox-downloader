from abc import ABC, abstractmethod
from typing import Generator, Optional, Union
from xml.etree.ElementTree import Element
import logging


class Downloader(ABC):
    def __init__(self):
        self.encoded: Optional[str] = None
        self.logger = logging.getLogger(type(self).__name__)

    @abstractmethod
    def get_keybox(self) -> Union[Element, Generator[Element]]:
        pass