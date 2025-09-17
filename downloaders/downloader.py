from abc import ABC, abstractmethod
from typing import Optional

class Downloader(ABC):
    def __init__(self):
        self.encoded: Optional[str] = None

    @abstractmethod
    def get_keybox(self) -> str:
        pass