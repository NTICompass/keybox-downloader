# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Specter download module."""

from base64 import b64decode
from datetime import datetime  # ruff: ignore[typing-only-standard-library-import]
from typing import TYPE_CHECKING, cast, final, override

from asyncstdlib import enumerate as a_enumerate
from httpx2 import ConnectError, HTTPStatusError, RequestError
from pydantic import UUID4, BaseModel, ConfigDict, Field

from . import Downloader

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class CatalogEntry(BaseModel):  # ruff: ignore[undocumented-public-class]
    model_config = ConfigDict(frozen=True)
    id: UUID4
    source: str
    version: str
    text: str
    revoked: bool
    softbanned: bool
    serial: str = Field(pattern=r'^[0-9a-fA-F]+$')
    last_checked: datetime
    timestamp: datetime
    rkp: bool
    expires_at: datetime | None = None  # Only `rkp` keys have an expiration


class CatalogWorking(BaseModel):  # ruff: ignore[undocumented-public-class]
    model_config = ConfigDict(frozen=True)
    source: str
    version: str


class CatalogWorkingEntry(CatalogWorking):  # ruff: ignore[undocumented-public-class]
    source: str
    version: str
    text: str = ''


class CatalogOverride(BaseModel):  # ruff: ignore[undocumented-public-class]
    model_config = ConfigDict(frozen=True)
    source: str


class Catalog(BaseModel):
    """Keybox catalog.

    Downloaded from: https://rawbin.dpejoh.com/catalog
    """

    model_config = ConfigDict(frozen=True)
    entries: list[CatalogEntry]
    latest: dict[str, str]
    working: CatalogWorking | None = None
    workingEntries: list[CatalogWorkingEntry] = []  # ruff: ignore[mixed-case-variable-in-class-scope]
    autoOverride: CatalogOverride | None = None  # ruff: ignore[mixed-case-variable-in-class-scope]


@final
class Specter(Downloader):
    """Specter Downloader.

    Telegram:
    https://t.me/dpejoh

    GitHub:
    https://github.com/dpejoh/specter

    Docs:
    https://specter.dpejoh.com/reference/config#urls
    """

    DESCRIPTION = 'Specter module (dpejoh @ GitHub, formerly worked on YuriKey)'
    URL = 'https://rawbin.dpejoh.com/catalog'
    URL_FALLBACK = 'https://rawbin.dpejoh.workers.dev/catalog'

    # Append `/source/version` to get that key, leave as-is to get "working" key
    KEYBOX_URL = 'https://rawbin.dpejoh.com/key'
    KEYBOX_URL_FALLBACK = 'https://rawbin.dpejoh.workers.dev/key'

    ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    SHUFFLED = '1dgWnocayqxU3r6vA5lCIPYfHmkV08b4tz+KMsp2NQ9LRXihODwSj7BEFJ/ZuGTe'

    @override
    def __init__(self) -> None:
        super().__init__()

        # 🏳️‍⚧️ PRIDE
        self.trans = str.maketrans(self.SHUFFLED, self.ALPHABET)
        self.extra_headers = {'User-Agent': 'Specter/1.0'}

    @override
    async def process(self, downloaded: AsyncGenerator[str]) -> AsyncGenerator[str | None]:
        self.logger.info('Downloading catalog')

        cat: Catalog | None
        cat_dl = await anext(downloaded, None)

        if cat_dl is None:
            try:
                fallback_cat = await self.client.get(
                    self.URL_FALLBACK, headers=cast('dict[str, str]', self.extra_headers)
                )
            except HTTPStatusError, ConnectError, RequestError:
                self.logger.info('Error downloading catalog')
                yield None
            else:
                cat_dl = fallback_cat.raise_for_status().text

        cat = Catalog.model_validate_json(cat_dl) if cat_dl is not None else None

        if cat is not None:
            other_keys = [
                f'{entry.source} v{entry.version}'
                for entry in cat.entries
                if not entry.revoked
                and not entry.softbanned
                and (cat.working.source if cat.working is not None else '') != entry.source
                and (cat.working.version if cat.working is not None else '') != entry.version
            ]

            self.logger.info(
                f'"Working" keybox is {cat.working.source if cat.working is not None else "none"} '
                f'v{cat.working.version if cat.working is not None else 0}'
            )

            if len(other_keys) > 0:
                self.logger.info(f'Other keys are {", ".join(other_keys)}')
            else:
                self.logger.info('No other keys')

            keys_to_get = [
                f'{entry.source}/{entry.version}' for entry in cat.entries if not entry.revoked and not entry.softbanned
            ]

            keys_downloaded = [False] * len(keys_to_get)

            async for idx, data in a_enumerate(
                self.download_urls(download=[f'{self.KEYBOX_URL}/{key_dl}' for key_dl in keys_to_get])
            ):
                keys_downloaded[idx] = True
                yield data

            if not all(keys_downloaded):
                keys_to_get_fallback = [
                    keys_to_get[idx] for idx, was_downloaded in enumerate(keys_downloaded) if not was_downloaded
                ]

                async for data in self.download_urls(
                    download=[f'{self.KEYBOX_URL_FALLBACK}/{key_dl}' for key_dl in keys_to_get_fallback]
                ):
                    yield data

    @override
    def decode(self, encoded: str) -> str:
        return b64decode(encoded.translate(self.trans)).decode('ascii')
