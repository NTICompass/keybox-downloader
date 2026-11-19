# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Extra classes for TrickyAddon cache."""

import re
from datetime import datetime  # ruff: ignore[typing-only-standard-library-import]
from typing import Literal

from pydantic import UUID4, BaseModel, ConfigDict, TypeAdapter, ValidationInfo, field_validator

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
