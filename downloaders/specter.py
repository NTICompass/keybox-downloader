from . import Downloader
from base64 import b64decode
from collections.abc import AsyncGenerator
from typing import final, override, TypedDict, NotRequired
import json


class CatalogEntries(TypedDict):
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
    entries: list[CatalogEntries]
    latest: dict[str, int]
    working: CatalogWorking
    autoOverride: CatalogOverride


@final
class Specter(Downloader):
    # https://github.com/dpejoh/specter/
    URL = 'https://rawbin.netlify.app/key/catalog'

    # Append `/source/version` to get that key, leave as-is to get "working" key
    KEYBOX_URL = 'https://rawbin.netlify.app/key'
    ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    SHUFFLED = '1dgWnocayqxU3r6vA5lCIPYfHmkV08b4tz+KMsp2NQ9LRXihODwSj7BEFJ/ZuGTe'

    @override
    def __init__(self):
        super().__init__()
        self.trans = str.maketrans(self.SHUFFLED, self.ALPHABET)

    @override
    async def process(
        self, downloaded: AsyncGenerator[str]
    ) -> AsyncGenerator[str | None]:
        self.logger.info('Downloading catalog')

        cat: Catalog = json.loads(await anext(downloaded))
        valid_keys = [
            f'{self.KEYBOX_URL}/{entry["source"]}/{entry["version"]}'
            for entry in cat['entries']
            if not entry['revoked']
        ]

        self.logger.info(
            f'Downloading "working" keybox: {cat["working"]["source"]} v{cat["working"]["version"]} as well as other non-revoked keyboxes'
        )

        # Manually downloading the current "working" key
        async for data in self.download_urls(download=valid_keys):
            yield data

    @override
    def decode(self, encoded: str) -> str:
        return b64decode(encoded.translate(self.trans)).decode('ascii')
