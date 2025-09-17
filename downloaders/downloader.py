from abc import ABC, abstractmethod
from typing import Generator, Optional, Union

class Downloader(ABC):
    def __init__(self):
        self.encoded: Optional[str] = None

    @abstractmethod
    def get_keybox(self) -> Union[str, Generator[str]]:
        pass