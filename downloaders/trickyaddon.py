# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""TrickyAddon download module."""

from contextlib import aclosing, asynccontextmanager
from datetime import datetime  # ruff: ignore[typing-only-standard-library-import]
from typing import TYPE_CHECKING, Literal, final, override

from pydantic import BaseModel, ConfigDict, ValidationError

from cache_data import TrickyAddon as TrickyCache
from cache_data.trickyaddon_extras import TokenDownloadError

from . import Downloader
from .utils import PeakSolver, SolverError

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from cache_data.trickyaddon_extras import DownloadToken


class RepoEntry(BaseModel):  # ruff: ignore[undocumented-public-class]
    model_config = ConfigDict(frozen=True)
    id: int
    status: Literal['valid', 'expired', 'revoked']
    root_type: Literal['hardware']
    nearest_expiry: datetime
    created_at: datetime
    download_count: int
    cert_count: int
    key_format: Literal['ecdsa', 'rsa', 'ecdsa,rsa']
    is_rkp: bool


class Repository(BaseModel):  # ruff: ignore[undocumented-public-class]
    model_config = ConfigDict(frozen=True)
    keyboxes: list[RepoEntry]
    total: int
    page: int
    per_page: int


@asynccontextmanager
async def dummy_context() -> AsyncGenerator[None]:  # ruff: ignore[undocumented-public-function]
    yield None


type DownloadURLs = AsyncGenerator[tuple[int, DownloadToken]]


@final
class TrickyAddon(Downloader):
    """TrickyAddon Downloader.

    Telegram:
    https://t.me/s/kowchannel

    GitHub:
    https://github.com/KOWX712/Tricky-Addon-Update-Target-List

    Keybox Repo:
    https://keybox.kowx712.cc

    Docs:
    https://github.com/KOWX712/Tricky-Addon-Update-Target-List/blob/main/webui/src/keybox/repo/repo-api.md
    """

    DESCRIPTION = 'Tricky Addon - Update Target List module (KOWX712 @ GitHub)'
    URL = 'https://keybox.kowx712.cc/api/keyboxes?search=&sort=status&page=1&limit=5'

    BASE_URL = 'https://keybox.kowx712.cc'

    @override
    def __init__(self) -> None:
        super().__init__()
        self.data_cache = TrickyCache()

    @override
    async def process(self, downloaded: AsyncGenerator[str]) -> AsyncGenerator[str | None]:
        repo: Repository | None
        self.logger.info('Downloading keybox list from repository')

        try:
            repo = Repository.model_validate_json(await anext(downloaded))
        except StopAsyncIteration:
            repo = None
            self.logger.info('Error downloading repository')

            yield None

        if repo is not None:
            valid: set[int] = {kb.id for kb in repo.keyboxes if kb.status == 'valid'}
            self.logger.info(f'Found {len(valid)} valid keyboxes out of {repo.total}')

            try:
                async with self.load_download_urls(valid) as load_urls:
                    downloads = {dl.url: key_id async for key_id, dl in load_urls}

                async for data in self.download_urls(download=list(downloads.keys())):
                    yield data
                    self.data_cache.remove_token(
                        downloads[self.current_url if isinstance(self.current_url, str) else str(self.current_url)]
                    )
            finally:
                self.data_cache.save()

    @asynccontextmanager
    async def load_download_urls(self, ids: set[int]) -> AsyncGenerator[DownloadURLs]:
        """Load the download tokens into the cache (if they are not there already).

        Args:
            ids: The ids to get tokens for.

        Yields:
            The token object for each id

        """
        if self.data_cache.keys is None:
            self.logger.info('Fetching Turnstile sitekey')
            keys = await self.client.get(f'{self.BASE_URL}/api/config')

            try:
                self.data_cache.save_site_key(keys.text)
            except ValidationError as err:
                self.logger.info(f'Error getting sitekeys: {err}')

        async with (
            PeakSolver(self.BASE_URL, self.data_cache.keys.turnstile_site_key)
            if self.data_cache.keys is not None
            else dummy_context()
        ) as solver:

            async def generate() -> DownloadURLs:
                for key_id in ids:
                    self.logger.info(f'Getting download token for keybox {key_id}')
                    cached_token = self.data_cache.get_token(key_id)

                    if cached_token is not None:
                        self.logger.info(f'Using cached token for keybox {key_id}')
                        yield key_id, cached_token
                    else:
                        if solver is None:
                            self.logger.info('Turnstile sitekey not found or solver not initialized')
                            continue

                        self.logger.info('Solving CloudFlare Turnstile challenge')
                        try:
                            challenge_result = await solver.challenge()
                            turnstile_token = challenge_result[0]
                        except SolverError as solve_err:
                            self.logger.info(f'CloudFlare Turnstile failed: {solve_err}')
                            continue

                        try:
                            if solver.proxy_client is None:
                                self.logger.info('Error getting proxy_client')
                                continue

                            self.logger.info(f'Downloading token for keybox {key_id} via proxy')
                            token = await solver.proxy_client.post(
                                f'{self.BASE_URL}/api/keyboxes/{key_id}/download',
                                headers={'Cf-Turnstile-Token': turnstile_token},
                            )

                            try:
                                download_token = self.data_cache.add_token(key_id, token.text, save=True)
                                self.logger.info(f'Saving download token for {key_id}: {download_token.token}')

                                yield key_id, download_token
                            except TokenDownloadError as token_err:
                                self.logger.info(f'Error downloading token: {token_err}')
                        except Exception as e:  # ruff: ignore[blind-except]
                            self.logger.info(f'Download error {e}')

            async with aclosing(generate()) as gen:
                yield gen

    @override
    def decode(self, encoded: str) -> str:
        msg = 'Keybox not encoded'
        raise NotImplementedError(msg)
