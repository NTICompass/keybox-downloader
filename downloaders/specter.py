from . import Downloader
from base64 import b64decode
from collections.abc import AsyncGenerator
from typing import final, override, TypedDict, NotRequired
import json


class CatalogEntry(TypedDict):
    source: str
    version: str
    text: str
    revoked: bool
    softbanned: NotRequired[bool]
    serial: str
    last_checked: str
    timestamp: str


class CatalogWorking(TypedDict):
    source: str
    version: str


class CatalogOverride(TypedDict):
    source: str


class Catalog(TypedDict):
    entries: list[CatalogEntry]
    latest: dict[str, int]
    working: CatalogWorking
    autoOverride: CatalogOverride


@final
class Specter(Downloader):
    # https://github.com/dpejoh/specter/
    # https://specter.dpejoh.com/reference/config.html
    URL = 'https://rawbin.netlify.app/key/catalog'

    # Append `/source/version` to get that key, leave as-is to get "working" key
    KEYBOX_URL = 'https://rawbin.netlify.app/key'
    ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    SHUFFLED = '1dgWnocayqxU3r6vA5lCIPYfHmkV08b4tz+KMsp2NQ9LRXihODwSj7BEFJ/ZuGTe'

    @override
    def __init__(self):
        super().__init__()

        # 🏳️‍⚧️ PRIDE
        self.trans = str.maketrans(self.SHUFFLED, self.ALPHABET)

    @property
    @override
    def description(self) -> str:
        return 'Specter module (dpejoh @ GitHub, formerly worked on YuriKey)'

    @override
    async def process(
        self, downloaded: AsyncGenerator[str]
    ) -> AsyncGenerator[str | None]:
        self.logger.info('Downloading catalog')

        cat: Catalog = json.loads(await anext(downloaded))
        other_keys = [
            f'{entry["source"]} v{entry["version"]}'
            for entry in cat['entries']
            if not entry['revoked']
            and cat['working']['source'] != entry['source']
            and cat['working']['version'] != entry['version']
        ]

        self.logger.info(
            f'"Working" keybox is {cat["working"]["source"]} v{cat["working"]["version"]}'
        )
        self.logger.info(f'Other keys are {", ".join(other_keys)}')

        async for data in self.download_urls(
            download=[
                f'{self.KEYBOX_URL}/{entry["source"]}/{entry["version"]}'
                for entry in cat['entries']
                if not entry['revoked']
            ]
        ):
            yield data

    @override
    def decode(self, encoded: str) -> str:
        return b64decode(encoded.translate(self.trans)).decode('ascii')
