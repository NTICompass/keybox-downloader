from downloaders import Downloader
from importlib.metadata import version
from typing import ClassVar


class Options:
    APP_VERSION: ClassVar[str] = version('keybox-downloader')
