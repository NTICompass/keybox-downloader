# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Token cache for TrickyAddon's repo."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, override

from .basedata import BaseData
from .trickyaddon_extras import (
    DLTokens,
    DownloadToken,
    SiteKeys,
    TokenDownloadError,
    download_response_adapter,
)


@dataclass
class TrickyAddon(BaseData[DLTokens]):
    """Saves each token with its expiration.  Removes it on use."""

    keys: SiteKeys | None = None
    tokens: DLTokens = field(default_factory=dict)
    _manifest_json = 'trickyaddon.json'

    def save_site_key(self, data: str, *, save: bool = False) -> SiteKeys:
        """Cache the sitekeys (I assume they're not going to change often).

        Args:
            data: The JSON from the site endpoint
            save: Save the file?

        Returns:
            The site keys

        """
        self.keys = SiteKeys.model_validate_json(data)

        if save:
            self.save()

        return self.keys

    def add_token(self, key_id: int, data: str, *, save: bool = False) -> DownloadToken:
        """Add a token to the cache, they are one-time use and expire in 24 hours.

        Args:
            key_id: The id from the repo
            data: The response from the endpoint (JSON)
            save: Save file after adding

        Returns:
            The added token

        Raises:
            TokenDownloadError: If the endpoint returns an error

        """
        response = download_response_adapter.validate_json(data)

        if isinstance(response, DownloadToken):
            self.tokens[key_id] = response

            if save:
                self.save()

            return response

        raise TokenDownloadError(response.error)

    def remove_token(self, key_id: int, *, save: bool = False) -> None:
        """Remove a token from the cache after using it.

        Args:
            key_id: The id from the repo
            save: Save file after removing

        """
        del self.tokens[key_id]

        if save:
            self.save()

    def get_token(self, key_id: int, *, save: bool = False) -> DownloadToken | None:
        """Get a token from the cache, so we don't need to request another one.

        Args:
            key_id: The id from the repo
            save: Auto-save the file?

        Returns:
            The token if it exists and it's not expired

        """
        token = self.tokens.get(key_id)

        if token is not None:
            if datetime.now(UTC) < token.expires_at:
                return token

            self.remove_token(key_id, save=save)

        return None

    @override
    def convert_for_save(self, name: str) -> dict[int, dict[str, Any]]:
        if name == 'tokens':
            return {keyid: data.model_dump(mode='json') for keyid, data in self.tokens.items()}
        return super().convert_for_save(name)
