from abc import ABC, abstractmethod
from asyncstdlib import enumerate as a_enumerate
from cache_data import Overrides
from cloudscraper import CloudScraper
from collections.abc import AsyncGenerator, Sequence
from httpx import AsyncClient, Response, URL as HTTP_URL, HTTPStatusError
from io import BytesIO
from program.keybox import Keybox, KeyboxMetadata, KeyboxError
from requests import Response as CloudflareResponse
from typing import final, overload, ClassVar, Literal, Self
from zipfile import Path as ZipPath
import asyncio
import logging
import re


def build_github_url(repo: str, branch: str, file: str) -> str:
    return f'https://raw.githubusercontent.com/{repo}/refs/heads/{branch if len(branch) > 0 else "main"}/{file}'


class Downloader(ABC):
    enabled: ClassVar[set[type[Self]]] = set()
    disabled: ClassVar[set[type[Self]]] = set()
    overrides: ClassVar[Overrides[type[Self]]] = Overrides()

    DESCRIPTION = ''
    URL: str
    URLS: list[str]
    ENABLED = True

    current_url: HTTP_URL | str
    client: ClassVar[AsyncClient] = AsyncClient(
        http2=True,
        follow_redirects=True,
        timeout=None,
        headers={
            'Accept-Encoding': 'br, gzip',
            'Cache-Control': 'no-cache',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
        },
    )
    cloudflare_client: ClassVar[CloudScraper] = CloudScraper()
    extra_headers: dict[str, str] | list[dict[str, str]] | None = None

    def __init__(self):
        self.logger = logging.getLogger(type(self).__name__)

    @final
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        override = Downloader.overrides.is_enabled(cls)
        is_enabled = cls.ENABLED if override is None else override
        target = Downloader.enabled if is_enabled else Downloader.disabled

        target.add(cls)

    @final
    async def __call__(self) -> AsyncGenerator[Keybox | None]:
        async for idx, data in a_enumerate(self.process(self.download_urls())):
            if data is None:
                yield None
            elif isinstance(data, str):
                try:
                    data = self.decode(data)
                except NotImplementedError:
                    pass

                try:
                    yield Keybox(
                        data, KeyboxMetadata(source=type(self).__name__, file_idx=idx)
                    )
                except KeyboxError as e:
                    self.logger.info(e.msg)
                    yield None
            else:
                yield data

    @abstractmethod
    def decode(self, encoded: str) -> str: ...

    def process(
        self, downloaded: AsyncGenerator[str]
    ) -> AsyncGenerator[str | Keybox | None]:
        self.logger.info(f'Downloaded keybox(es) for {type(self).__name__}')
        return downloaded

    @final
    def unzip(self, zipfile: bytes, filename: str) -> Keybox:
        zip_file = ZipPath(BytesIO(zipfile), at=filename)

        with zip_file.open('r') as data:
            self.logger.info('Extracting keybox from ZIP file')
            return Keybox(
                data,
                KeyboxMetadata(
                    source=type(self).__name__, original=zip_file, file_idx=1
                ),
            )

    @final
    def get_var_from_shell(self, script: str | bytes, var: list[str]) -> dict[str, str]:
        return dict(re.findall(rf'(?<! )({"|".join(var)})="(.+?)"', str(script)))

    @final
    def get_headers(self, idx: int) -> dict[str, str]:
        if self.extra_headers is None:
            return {}
        elif isinstance(self.extra_headers, dict):
            return self.extra_headers
        else:
            return self.extra_headers[idx]

    @final
    async def download_all(self, *download: str) -> AsyncGenerator[Response]:
        for r in await asyncio.gather(
            *[
                self.client.get(
                    build_github_url(*dl.split(':', 4)[1:])
                    if dl.startswith('github:')
                    else dl,
                    headers=self.get_headers(idx),
                )
                for idx, dl in enumerate(download)
            ]
        ):
            try:
                r.raise_for_status()
            except HTTPStatusError as exc:
                self.logger.info(
                    f'Error response {exc.response.status_code} while requesting {exc.request.url!r}.'
                )
            else:
                yield r

    @final
    async def cloudflare_download(
        self, *download: str
    ) -> AsyncGenerator[CloudflareResponse]:
        for r in await asyncio.gather(
            *[
                asyncio.to_thread(
                    self.cloudflare_client.get,
                    dl,
                    headers=self.get_headers(idx),
                )
                for idx, dl in enumerate(download)
            ]
        ):
            self.logger.info(f'Downloaded {r.url} via "CloudScraper"')
            yield r

    @overload
    def download_urls(
        self,
        binary: Literal[True],
        cloudflare: bool = False,
        download: Sequence[str] | None = None,
    ) -> AsyncGenerator[bytes]: ...

    @overload
    def download_urls(
        self,
        binary: Literal[False] = False,
        cloudflare: bool = False,
        download: Sequence[str] | None = None,
    ) -> AsyncGenerator[str]: ...

    @final
    async def download_urls(
        self,
        binary: bool = False,
        cloudflare: bool = False,
        download: Sequence[str] | None = None,
    ) -> AsyncGenerator[str | bytes]:
        if download is None:
            try:
                download = self.URLS
            except AttributeError:
                download = (self.URL,)

        if download is not None:
            async for r in (
                self.cloudflare_download(*download)
                if cloudflare
                else self.download_all(*download)
            ):
                self.current_url = r.url
                yield r.content if binary else r.text
