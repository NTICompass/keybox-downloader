from abc import ABC, abstractmethod
from typing import Generator, Optional, Union
from xml.etree.ElementTree import Element

class Downloader(ABC):
    def __init__(self):
        self.encoded: Optional[str] = None

    @abstractmethod
    def get_keybox(self) -> Union[Element, Generator[Element]]:
        pass