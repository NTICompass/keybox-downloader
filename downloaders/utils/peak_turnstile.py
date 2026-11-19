# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Solve Cloudflare Turnstile challenges with peak.fo."""

from typing import TYPE_CHECKING, Annotated, Literal, Self, final

from httpx2 import AsyncClient
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from downloaders import Downloader

if TYPE_CHECKING:
    from types import TracebackType


class TurnstileTokens(BaseModel):  # ruff: ignore[undocumented-public-class]
    model_config = ConfigDict(frozen=True)
    token: str
    secondary_token: str | None = None


class TurnstileSuccess(BaseModel):  # ruff: ignore[undocumented-public-class]
    model_config = ConfigDict(frozen=True)
    success: Literal[True]
    data: TurnstileTokens


class TurnstileError(BaseModel):  # ruff: ignore[undocumented-public-class]
    model_config = ConfigDict(frozen=True)
    success: Literal[False]
    error: str
    error_code: str


turnstile_response = TypeAdapter(
    Annotated[
        TurnstileSuccess | TurnstileError,
        Field(discriminator='success'),
    ]
)


class SolverError(BaseException): ...  # ruff: ignore[undocumented-public-class]


@final
class PeakSolver:
    """Use Peak's API to solve Turnstile challenges.  Requires an API key and an HTTP(S) proxy."""

    API_URL = 'https://api.peak.fo/solve'
    API_TASK = 'turnstiletask'

    proxy_client: AsyncClient | None = None

    def __init__(self, url: str, site_key: str) -> None:
        """Configure the solver with the url & site key.

        Args:
            url: The URL to run the challenge/solver on
            site_key: Cloudflare Turnstile sitekey

        """
        self.url = url.rstrip('/') + '/'  # Make sure URL ends with a slash
        self.site_key = site_key

    async def __aenter__(self) -> Self:
        """Allow `async with PeakSolver() as solver: ...`.

        Returns:
            The `PeakSolver` instance

        """
        return self

    async def __aexit__(
        self, _exc_type: type[BaseException] | None, _exc_value: BaseException | None, _traceback: TracebackType | None
    ) -> None:
        """Close the httpx2 client (if opened) after `async with`."""
        if self.proxy_client is not None:
            await self.proxy_client.aclose()

    async def challenge(self) -> tuple[str, ...]:
        """Solves a Turnstile challenge and returns the token(s).

        Returns:
            The token and possible secondary token from the challenge.

        Raises:
            SolverError: On misconfiguration or failures

        """
        peak_api, peak_proxy = await Downloader.get_peak_token()

        if peak_api is None or peak_proxy is None:
            msg = 'No API key or Proxy found'
            raise SolverError(msg)

        turnstile = await Downloader.client.post(
            self.API_URL,
            json={
                'task_type': self.API_TASK,
                'url': self.url,
                'sitekey': self.site_key,
                'proxy': peak_proxy,
            },
            headers={'X-API-Key': peak_api, 'Content-Type': 'application/json'},
        )

        response = turnstile_response.validate_json(turnstile.text)

        if isinstance(response, TurnstileError):
            msg = f'Error solving challenge: {response.error}'
            raise SolverError(msg)

        if self.proxy_client is None:
            self.proxy_client = AsyncClient(proxy=peak_proxy, timeout=30)

        if response.data.secondary_token is not None:
            return response.data.token, response.data.secondary_token

        return (response.data.token,)
