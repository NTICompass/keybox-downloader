# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Downloader base class, does all the work and makes adding new download modules easy."""

import asyncio
import logging
import os
import re
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from io import BytesIO
from typing import TYPE_CHECKING, ClassVar, Literal, Self, final, overload
from zipfile import Path as ZipPath
from zipfile import ZipFile

from asyncstdlib import enumerate as a_enumerate
from cloudscraper import CloudScraper
from dotenv import load_dotenv
from httpx2 import URL as HTTP_URL
from httpx2 import AsyncClient, HTTPStatusError
from pydantic import BaseModel, ConfigDict

import __main__
from cache_data import Overrides
from program.keybox import Keybox, KeyboxError, KeyboxMetadata

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Sequence
    from pathlib import Path

    from httpx2 import Response as HttpResponse
    from requests import Response as CloudflareResponse
    from requests import Session


class GitHubAsset(BaseModel):
    """Validate JSON for each asset in a release."""

    model_config = ConfigDict(extra='allow', frozen=True)
    name: str
    digest: str | None = None
    content_type: str
    browser_download_url: str


class GitHubRelease(BaseModel):
    """Validate the release data from GitHub API.

    Docs: https://docs.github.com/en/rest/releases/releases?apiVersion=2026-03-10
    """

    model_config = ConfigDict(extra='allow', frozen=True)
    assets: list[GitHubAsset]


def build_github_url(repo: str, branch: str, file: str) -> str:
    """Convert "shorthand" `github:` URL into a direct (raw) download link.

    Args:
        repo: Repository name
        branch: Branch name
        file: File name

    Returns:
        Raw download URL

    """
    return f'https://raw.githubusercontent.com/{repo}/refs/heads/{branch if len(branch) > 0 else "main"}/{file}'


def build_github_api_url(repo: str) -> str:
    """Convert "shorthand" `github-api:` URL into the URL for the latest release.

    Args:
        repo: Repository name

    Returns:
        JSON data for latest release (validated via `GitHubRelease`)

    """
    return f'https://api.github.com/repos/{repo}/releases/latest'


def get_download_url(dl: str) -> str:
    """Get the URL to download.

    Args:
        dl: URL to look up (could be a `github:` or `github-api:` shorthand)

    Returns:
        Normalized URL

    """
    if dl.startswith('github:'):
        return build_github_url(*dl.split(':', 4)[1:])
    if dl.startswith('github-api:'):
        return build_github_api_url(dl.split(':', 1)[1])
    return dl


class Downloader(ABC):
    """To implement: set `DESCRIPTION` and `URL` and implement `decode(self, encoded: str) -> str`."""

    enabled: ClassVar[set[type[Self]]] = set()
    disabled: ClassVar[set[type[Self]]] = set()
    overrides: ClassVar[Overrides[type[Self]]] = Overrides[type[Self]]()

    env_file: ClassVar[Path] = __main__.exe_root / '.env'
    _env_loaded: ClassVar[bool] = False

    client: ClassVar[AsyncClient]
    cloudflare_client: ClassVar[CloudScraper | Session]

    DESCRIPTION = ''
    URL: str
    URLS: list[str]

    current_url: HTTP_URL | str
    extra_headers: dict[str, str] | list[dict[str, str]] | None = None

    def __init__(self) -> None:
        """Init the `logger`, child classes can override `__init__` if needed."""
        self.logger = logging.getLogger(type(self).__name__)

    @final
    def __init_subclass__(cls, *, enabled: bool = True) -> None:
        """Add each `Downloader` subclass to the `registry`, can be overridden using `Overrides` (options menu).

        Args:
            enabled: Set to `False` to disable subclass

        """
        super().__init_subclass__()

        override = Downloader.overrides.is_enabled(cls)
        is_enabled = enabled if override is None else override
        target = Downloader.enabled if is_enabled else Downloader.disabled

        target.add(cls)

    @final
    @classmethod
    @asynccontextmanager
    async def start(cls) -> AsyncIterator[None]:
        """Context manger to open/close the `httpx2` and `cloudscraper` modules."""
        async with AsyncExitStack() as stack:
            cls.client = await stack.enter_async_context(
                AsyncClient(
                    http2=True,
                    follow_redirects=True,
                    timeout=None,
                    headers={
                        'Accept-Encoding': 'zstd, br, gzip',
                        'Cache-Control': 'no-cache',
                        # https://android-developers.googleblog.com/2024/12/user-agent-reduction-on-android-webview.html
                        # https://whatmyuseragent.com/platforms/android
                        'User-Agent': 'Mozilla/5.0 (Linux; Android 17; Pixel 9 Pro Build/CP2A.260605.012; wv) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Version/4.0 Chrome/149.0.7827.164 Mobile Safari/537.36',
                    },
                )
            )
            cls.cloudflare_client = stack.enter_context(CloudScraper())
            yield

    @final
    async def run(self) -> AsyncIterator[Keybox | None]:
        """Run the downloader.

        Renamed to `run()` from `__call__()` due to PyCharm bug:
        https://youtrack.jetbrains.com/issue/PY-89873

        Yields:
            `Keybox` or `None`

        """
        async for idx, data in a_enumerate(self.process(self.download_urls())):
            if data is None:
                yield None
            elif isinstance(data, str):
                with suppress(NotImplementedError):
                    data = self.decode(data)  # ruff:ignore[redefined-loop-name]

                try:
                    yield Keybox(data, KeyboxMetadata(source=type(self).__name__, file_idx=idx))
                except KeyboxError as e:
                    self.logger.info(str(e))
                    yield None
            else:
                yield data

    @abstractmethod
    def decode(self, encoded: str) -> str:
        """Decode an encoded keybox.

        Args:
            encoded: Encoded keybox

        Returns:
            Decoded keybox.xml

        """

    def process(self, downloaded: AsyncGenerator[str]) -> AsyncGenerator[str | Keybox | None]:
        """Process each downloaded URL and send to `decode()` method, can be overridden.

        Args:
            downloaded: An `AsyncGenerator` yielding each downloaded URL's contents

        Returns:
            `AsyncGenerator` yielding XML strings, `Keybox` objects or `None`

        """
        self.logger.info(f'Downloaded keybox(es) for {type(self).__name__}')
        return downloaded

    @final
    @classmethod
    def get_github_token(cls) -> str | None:
        """Use `GITHUB_TOKEN` from the environment for the GitHub API.

        Returns:
            `GITHUB_TOKEN` from the envrionment (if set)

        """
        if not cls._env_loaded:
            load_dotenv(cls.env_file if cls.env_file.exists() else None)
            cls._env_loaded = True

        return os.getenv('GITHUB_TOKEN')

    @final
    async def get_latest_github_release(self, data: GitHubRelease | dict | str) -> bytes | None:
        """Parse the data from the GitHub API and download the latest release's ZIP file.

        Args:
            data: The response from the GitHub API (JSON string, parsed `dict` or validated `GitHubRelease` object)

        Returns:
            Zip file (as `bytes`) or `None`

        """
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
                    # TODO: Check using `hash = release.digest`  # ruff: ignore[line-contains-todo]
                    return await anext(self.download_urls(binary=True, download=[release.browser_download_url]))
                finally:
                    self.extra_headers = orig_headers

        return None

    @final
    def unzip_keybox(self, zipfile: bytes, filename: str = 'keybox.xml') -> Keybox:
        """Extract a keybox from a Zip file.

        Args:
            zipfile: Zip file data (as `bytes`)
            filename: File path to open inside zip file

        Returns:
            `Keybox` object

        """
        zip_file = ZipPath(BytesIO(zipfile), at=filename)

        with zip_file.open('r') as data:
            self.logger.info('Extracting keybox from ZIP file')
            return Keybox(data, KeyboxMetadata(source=type(self).__name__, original=zip_file, file_idx=1))

    @final
    def unzip_files(self, zipfile: bytes, filenames: list[str]) -> list[str]:  # ruff: ignore[no-self-use]
        """Extract a list of files from a Zip file.

        Args:
            zipfile: Zip file data (as `bytes`)
            filenames: List of files to extract

        Returns:
            List of file contents (in the same order as `filenames`)

        """
        files = []
        with ZipFile(BytesIO(zipfile)) as zf:
            for filename in filenames:
                with zf.open(filename) as data:
                    files.append(data.read().decode('utf-8'))

        return files

    @final
    def get_var_from_shell(self, script: str | bytes, var: list[str]) -> dict[str, str]:  # ruff: ignore[no-self-use]
        """Extract values from a Unix shell script (like `ABC="xyz"`).

        Args:
            script: The script text
            var: The vars to extract

        Returns:
            A map of vars to their values

        """
        return dict(re.findall(rf'(?<! )({"|".join(var)})="(.+?)"', str(script)))

    @final
    def _get_headers(self, idx: int) -> dict[str, str]:
        """Get the headers for each URL download request (can be overriden/extended via `extra_headers`).

        Args:
            idx: Which URL to download (since you can have different headers per-URL)

        Returns:
            A map of headers and their values

        """
        if self.extra_headers is None:
            return {}
        if isinstance(self.extra_headers, dict):
            return self.extra_headers
        return self.extra_headers[idx]

    @final
    async def _download_all(self, *download: str) -> AsyncIterator[HttpResponse]:
        """Fire off all downloads in parallel using `httpx2`.

        Args:
            download: URLs to download

        Yields:
            The `Response` from each download, in order

        """
        for r in await asyncio.gather(
            *[self.client.get(get_download_url(dl), headers=self._get_headers(idx)) for idx, dl in enumerate(download)]
        ):
            try:
                r.raise_for_status()
            except HTTPStatusError as exc:
                self.logger.info(f'Error response {exc.response.status_code} while requesting {exc.request.url!r}.')
            else:
                yield r

    @final
    async def _cloudflare_download(self, *download: str) -> AsyncIterator[CloudflareResponse]:
        """Fire off all downloads in parallel using `cloudscraper` (to bypass Cloudflare Turnstile).

        Args:
            download: URLs to download

        Yields:
            The `Response` from each download, in order

        """
        for r in await asyncio.gather(
            *[
                asyncio.to_thread(self.cloudflare_client.get, dl, headers=self._get_headers(idx))
                for idx, dl in enumerate(download)
            ]
        ):
            self.logger.info(f'Downloaded {r.url} via "CloudScraper"')
            yield r

    @overload
    def download_urls(
        self, *, binary: Literal[True], cloudflare: bool = False, download: Sequence[str] | None = None
    ) -> AsyncGenerator[bytes]: ...

    @overload
    def download_urls(
        self, *, binary: Literal[False] = False, cloudflare: bool = False, download: Sequence[str] | None = None
    ) -> AsyncGenerator[str]: ...

    @final
    async def download_urls(
        self, *, binary: bool = False, cloudflare: bool = False, download: Sequence[str] | None = None
    ) -> AsyncGenerator[str | bytes]:
        """Download urls, either from `URL`/`URLS` or the `download` parameter.

        Args:
            binary: `True` to return `bytes`, `False` to return `str`
            cloudflare: `True` to use `cloudscraper`
            download: List of URLs to download

        Yields:
            Either `str` or `bytes` depending on `binary`

        """
        if download is None:
            try:
                download = self.URLS
            except AttributeError:
                download = (self.URL,)

        if download is not None:
            async for r in self._cloudflare_download(*download) if cloudflare else self._download_all(*download):
                self.current_url = r.url
                yield r.content if binary else r.text
