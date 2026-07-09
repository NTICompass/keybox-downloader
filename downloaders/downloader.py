from abc import ABC, abstractmethod
from asyncstdlib import enumerate as a_enumerate
from cache_data import Overrides
from cloudscraper import CloudScraper
from collections.abc import AsyncGenerator, Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from dotenv import load_dotenv
from httpx2 import AsyncClient, Response, URL as HTTP_URL, HTTPStatusError
from io import BytesIO
from pathlib import Path
from program.keybox import Keybox, KeyboxMetadata, KeyboxError
from pydantic import BaseModel, ConfigDict
from requests import Response as CloudflareResponse, Session
from typing import final, overload, ClassVar, Literal, Self
from zipfile import Path as ZipPath, ZipFile
import __main__
import asyncio
import logging
import os
import re


# https://docs.github.com/en/rest/releases/releases?apiVersion=2026-03-10
class GitHubAsset(BaseModel):
    model_config = ConfigDict(extra='allow', frozen=True)

    name: str
    digest: str | None = None
    content_type: str
    browser_download_url: str


class GitHubRelease(BaseModel):
    model_config = ConfigDict(extra='allow', frozen=True)

    assets: list[GitHubAsset]


def build_github_url(repo: str, branch: str, file: str) -> str:
    return f'https://raw.githubusercontent.com/{repo}/refs/heads/{branch if len(branch) > 0 else "main"}/{file}'


def build_github_api_url(repo: str) -> str:
    return f'https://api.github.com/repos/{repo}/releases/latest'


def get_download_url(dl: str) -> str:
    if dl.startswith('github:'):
        return build_github_url(*dl.split(':', 4)[1:])
    elif dl.startswith('github-api:'):
        return build_github_api_url(dl.split(':', 1)[1])
    else:
        return dl


class Downloader(ABC):
    enabled: ClassVar[set[type[Self]]] = set()
    disabled: ClassVar[set[type[Self]]] = set()
    overrides: ClassVar[Overrides[type[Self]]] = Overrides()

    env_file: ClassVar[Path] = __main__.exe_root / '.env'
    _env_loaded: ClassVar[bool] = False

    client: ClassVar[AsyncClient]
    cloudflare_client: ClassVar[CloudScraper | Session]

    DESCRIPTION = ''
    URL: str
    URLS: list[str]

    current_url: HTTP_URL | str
    extra_headers: dict[str, str] | list[dict[str, str]] | None = None

    def __init__(self):
        self.logger = logging.getLogger(type(self).__name__)

    @final
    def __init_subclass__(cls, enabled=True, **kwargs):
        super().__init_subclass__(**kwargs)

        override = Downloader.overrides.is_enabled(cls)
        is_enabled = enabled if override is None else override
        target = Downloader.enabled if is_enabled else Downloader.disabled

        target.add(cls)

    @final
    @classmethod
    @asynccontextmanager
    async def start(cls):
        async with AsyncExitStack() as stack:
            cls.client = await stack.enter_async_context(
                AsyncClient(
                    http2=True,
                    follow_redirects=True,
                    timeout=None,
                    headers={
                        'Accept-Encoding': 'zstd, br, gzip',
                        'Cache-Control': 'no-cache',
                        'User-Agent': 'Mozilla/5.0 (Linux; Android 17; Pixel 9 Pro Build/CP2A.260605.012; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/149.0.7827.164 Mobile Safari/537.36',
                    },
                )
            )
            cls.cloudflare_client = stack.enter_context(CloudScraper())
            yield

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
    @classmethod
    def get_github_token(cls) -> str | None:
        if not cls._env_loaded:
            load_dotenv(cls.env_file if cls.env_file.exists() else None)
            cls._env_loaded = True

        return os.getenv('GITHUB_TOKEN')

    @final
    async def get_latest_github_release(
        self, data: GitHubRelease | dict | str
    ) -> bytes | None:
        self.logger.info('Searching for latest release')

        releases: GitHubRelease | None = None

        if isinstance(data, GitHubRelease):
            releases = data
        elif isinstance(data, str):
            releases = GitHubRelease.model_validate_json(data)
        elif isinstance(data, dict):
            releases = GitHubRelease.model_validate(data)

        if releases is None:
            return None

        for release in releases.assets:
            if release.content_type == 'application/zip':
                self.logger.info(f'Downloading {release.name}')

                orig_headers = self.extra_headers
                self.extra_headers = None

                try:
                    # hash = release.digest
                    return await anext(
                        self.download_urls(
                            binary=True,
                            download=[release.browser_download_url],
                        )
                    )
                finally:
                    self.extra_headers = orig_headers

        return None

    @final
    def unzip_keybox(self, zipfile: bytes, filename: str = 'keybox.xml') -> Keybox:
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
    def unzip_files(self, zipfile: bytes, filenames: list[str]) -> list[str]:
        files = []
        with ZipFile(BytesIO(zipfile)) as zf:
            for filename in filenames:
                with zf.open(filename) as data:
                    files.append(data.read().decode('utf-8'))

        return files

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
                    get_download_url(dl),
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
