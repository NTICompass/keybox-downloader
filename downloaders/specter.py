from . import Downloader
from base64 import b64decode
from collections.abc import AsyncGenerator
from datetime import datetime
from pydantic import BaseModel, UUID4, Field, ConfigDict
from typing import final, override


class CatalogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID4
    source: str
    version: str
    text: str
    revoked: bool
    softbanned: bool
    shared: bool
    serial: str = Field(pattern=r'^[0-9a-fA-F]+$')
    last_checked: datetime
    timestamp: datetime


class CatalogWorking(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    version: str


class CatalogWorkingEntry(CatalogWorking):
    text: str


class CatalogOverride(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str


class Catalog(BaseModel):
    model_config = ConfigDict(frozen=True)

    entries: list[CatalogEntry]
    latest: dict[str, str]
    working: CatalogWorking | None = None
    workingEntries: list[CatalogWorkingEntry]
    autoOverride: CatalogOverride | None = None
    shared: bool


@final
class Specter(Downloader):
    # https://github.com/dpejoh/specter/
    # https://specter.dpejoh.com/reference/config.html
    DESCRIPTION = 'Specter module (dpejoh @ GitHub, formerly worked on YuriKey)'
    # https://rawbin.netlify.app/key/catalog
    URL = 'https://rawbin.dpejoh.com/catalog'

    # Append `/source/version` to get that key, leave as-is to get "working" key
    KEYBOX_URL = 'https://rawbin.dpejoh.com/key'
    ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    SHUFFLED = '1dgWnocayqxU3r6vA5lCIPYfHmkV08b4tz+KMsp2NQ9LRXihODwSj7BEFJ/ZuGTe'

    extra_headers = {'User-Agent': 'Specter/1.0'}

    @override
    def __init__(self):
        super().__init__()

        # 🏳️‍⚧️ PRIDE
        self.trans = str.maketrans(self.SHUFFLED, self.ALPHABET)

    @override
    async def process(
        self, downloaded: AsyncGenerator[str]
    ) -> AsyncGenerator[str | None]:
        cat: Catalog | None
        self.logger.info('Downloading catalog')

        try:
            cat = Catalog.model_validate_json(await anext(downloaded))
        except StopAsyncIteration:
            cat = None
            self.logger.info('Error downloading catalog')

            yield None

        if cat is not None:
            other_keys = [
                f'{entry.source} v{entry.version}'
                for entry in cat.entries
                if not entry.revoked
                and not entry.softbanned
                and (cat.working.source if cat.working is not None else '')
                != entry.source
                and (cat.working.version if cat.working is not None else '')
                != entry.version
            ]

            self.logger.info(
                f'"Working" keybox is {cat.working.source if cat.working is not None else "none"} v{cat.working.version if cat.working is not None else 0}'
            )

            if len(other_keys) > 0:
                self.logger.info(f'Other keys are {", ".join(other_keys)}')
            else:
                self.logger.info('No other keys')

            async for data in self.download_urls(
                download=[
                    f'{self.KEYBOX_URL}/{entry.source}/{entry.version}'
                    for entry in cat.entries
                    if not entry.revoked and not entry.softbanned
                ]
            ):
                yield data

    @override
    def decode(self, encoded: str) -> str:
        return b64decode(encoded.translate(self.trans)).decode('ascii')
