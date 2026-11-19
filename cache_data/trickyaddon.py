# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Token cache for TrickyAddon's repo."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, override

from pydantic import UUID4, BaseModel, ConfigDict, TypeAdapter, ValidationInfo, field_validator

from .basedata import BaseData

uuid4_adapter = TypeAdapter(UUID4)


class SiteKeys(BaseModel):  # ruff: ignore[undocumented-public-class]
    model_config = ConfigDict(frozen=True)
    recaptcha_site_key: str
    turnstile_site_key: str


class DownloadToken(BaseModel):  # ruff: ignore[undocumented-public-class]
    model_config = ConfigDict(frozen=True)
    token: UUID4
    url: str
    expires_at: datetime
    created_at: Literal['0001-01-01T00:00:00Z']

    @field_validator('url')
    @classmethod
    def validate_url(cls, value: str, info: ValidationInfo) -> str:  # ruff: ignore[undocumented-public-method]
        match = re.search(r'^.+?/download/(.+?)$', value)

        if match is None:
            msg = 'Must contain /download/'
            raise ValueError(msg)

        try:
            url_token = uuid4_adapter.validate_python(match.group(1))
        except ValueError as err:
            msg = 'Must contain a valid UUID4'
            raise ValueError(msg) from err

        token: UUID4 | None = info.data.get('token')

        if token is not None and url_token != token:
            msg = 'UUID must match token'
            raise ValueError(msg)

        return match.group(0)


class DownloadError(BaseModel):  # ruff: ignore[undocumented-public-class]
    model_config = ConfigDict(frozen=True)
    error: str


class TokenDownloadError(Exception): ...  # ruff: ignore[undocumented-public-class]


download_response_adapter = TypeAdapter(DownloadToken | DownloadError)

type DLTokens = dict[int, DownloadToken]


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
