# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""TrickyAddon download module."""

from datetime import datetime  # ruff: ignore[typing-only-standard-library-import]
from typing import TYPE_CHECKING, Literal, final, override

from httpx2 import AsyncClient
from pydantic import BaseModel, ConfigDict, ValidationError

from cache_data import TokenDownloadError
from cache_data import TrickyAddon as TrickyCache

from . import Downloader

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from cache_data import DownloadToken


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


@final
class TrickyAddon(Downloader, enabled=False):
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
                downloads = {dl.url: key_id async for key_id, dl in self.load_download_urls(valid)}
                async for data in self.download_urls(download=list(downloads.keys())):
                    yield data
                    self.data_cache.remove_token(
                        downloads[self.current_url if isinstance(self.current_url, str) else str(self.current_url)]
                    )
            finally:
                self.data_cache.save()

    async def load_download_urls(self, ids: set[int]) -> AsyncGenerator[tuple[int, DownloadToken]]:
        """Load the download tokens into the cache (if they are not there already).

        Args:
            ids: The ids to get tokens for.

        Yields:
            The token object for each id

        """
        peak_api, peak_proxy = await self.get_peak_token()
        if peak_api is None or peak_proxy is None:
            self.logger.info('peak.fo api key/proxy not found')
            return

        proxy_client = AsyncClient(proxy=peak_proxy, timeout=30)

        try:
            if self.data_cache.keys is None:
                self.logger.info('Fetching Turnstile sitekey')
                keys = await self.client.get('https://keybox.kowx712.cc/api/config')

                try:
                    self.data_cache.save_site_key(keys.text)
                except ValidationError as err:
                    self.logger.info(f'Error getting sitekeys: {err}')

            for key_id in ids:
                self.logger.info(f'Getting download token for keybox {key_id}')
                cached_token = self.data_cache.get_token(key_id)

                if cached_token is not None:
                    self.logger.info(f'Using cached token for keybox {key_id}')
                    yield key_id, cached_token
                else:
                    if self.data_cache.keys is None:
                        self.logger.info('Turnstile sitekey not found')
                        continue

                    self.logger.info('Solving CloudFlare Turnstile challenge')
                    turnstile = await self.client.post(
                        'https://api.peak.fo/solve',
                        json={
                            'task_type': 'turnstiletask',
                            'url': 'https://keybox.kowx712.cc/',
                            'sitekey': self.data_cache.keys.turnstile_site_key,
                            'proxy': peak_proxy,
                        },
                        headers={'X-API-Key': peak_api, 'Content-Type': 'application/json'},
                    )

                    # TODO: Parse with pydantic  # ruff: ignore[line-contains-todo]
                    """
                    Error Response: {'error': 'Proxy connection failed - verify proxy format (http://user:pass@ip:port) and availability', 'error_code': 'proxy_error', 'success': False}
                    """
                    turnstile_data = turnstile.json()
                    if not turnstile_data['success']:
                        self.logger.info(f'CloudFlare Turnstile failed: {turnstile_data["error"]}')
                        return

                    self.logger.info('CloudFlare Turnstile completed')
                    turnstile_token = turnstile_data['data']['token']  # also `secondary_token`

                    try:
                        self.logger.info(f'Downloading token for keybox {key_id} via proxy')
                        token = await proxy_client.post(
                            f'{self.BASE_URL}/api/keyboxes/{key_id}/download',
                            headers={'Cf-Turnstile-Token': str(turnstile_token)},
                        )

                        try:
                            download_token = self.data_cache.add_token(key_id, token.text, save=True)
                            self.logger.info(f'Saving download token for {key_id}: {download_token.token}')

                            yield key_id, download_token
                        except TokenDownloadError as err:
                            self.logger.info(f'Error downloading token: {err}')
                    except Exception as e:  # ruff: ignore[blind-except]
                        self.logger.info(f'Download error {e}')
        finally:
            await proxy_client.aclose()

    @override
    def decode(self, encoded: str) -> str:
        msg = 'Keybox not encoded'
        raise NotImplementedError(msg)
