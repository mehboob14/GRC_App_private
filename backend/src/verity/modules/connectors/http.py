"""Shared outbound HTTP for every connector (docs/architecture/integrations.md).

One place for what every provider call needs: a timeout, retry with exponential
backoff and full jitter on transient failures, paging through ``Link`` headers,
and one error vocabulary. A connector never writes its own retry loop, because a
retry storm against a rate limited provider gets the customer's account throttled.

Every error here becomes an ``error`` result, never ``fail`` (rule 7): it says
Verity could not tell, not that the control failed. Messages are written for the
person reading the control page and never carry a credential.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from typing import Any, Final

import httpx

_RETRYABLE_STATUS: Final = frozenset({500, 502, 503, 504})
_MAX_RETRY_AFTER_SECONDS: Final = 60.0
_BACKOFF_BASE_SECONDS: Final = 0.5
_BACKOFF_CAP_SECONDS: Final = 8.0


class ProviderError(Exception):
    """A provider call that did not produce an answer. ``str()`` is safe to show.

    ``provider_message`` is the provider's own wording, kept for the rare caller
    that must tell two meanings of one status apart.
    """

    provider_message: str = ""


class CredentialRejected(ProviderError):
    """401: the token is wrong, revoked or expired."""


class AccessDenied(ProviderError):
    """403 without a rate limit: the token lacks a permission this call needs."""


class NotFoundError(ProviderError):
    """404. Some providers use it to mean "not enabled", so callers may catch it."""


class RateLimitExhausted(ProviderError):
    """The provider's hourly allowance is spent; retrying now only makes it worse."""


class ProviderUnavailable(ProviderError):
    """The provider kept failing or could not be reached."""


def _next_link(response: httpx.Response) -> str | None:
    link = response.links.get("next")
    return link.get("url") if link else None


class ProviderHttp:
    """A thin client around ``httpx.AsyncClient`` with the shared behaviour.

    ``transport`` lets tests replay recorded responses; ``sleep`` lets them skip
    the waiting. Neither is used in production.
    """

    def __init__(  # noqa: PLR0913 — connection settings, each with a default
        self,
        base_url: str,
        *,
        headers: Mapping[str, str],
        timeout: float,
        max_retries: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=dict(headers),
            timeout=timeout,
            transport=transport,
            follow_redirects=True,
        )
        self._max_retries = max_retries
        self._sleep = sleep
        self.last_response: httpx.Response | None = None

    async def __aenter__(self) -> ProviderHttp:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self._client.aclose()

    async def get(self, path: str, params: Mapping[str, Any] | None = None) -> httpx.Response:
        """GET with retry. Returns a 2xx response or raises a classified error."""
        attempt = 0
        while True:
            try:
                response = await self._client.get(path, params=params)
            except httpx.TransportError as exc:
                if attempt >= self._max_retries:
                    raise ProviderUnavailable("The provider could not be reached.") from exc
                await self._backoff(attempt)
                attempt += 1
                continue

            self.last_response = response
            if response.is_success:
                return response
            wait = self._retry_after(response)
            if wait is not None and attempt < self._max_retries:
                await self._sleep(wait)
                attempt += 1
                continue
            if response.status_code in _RETRYABLE_STATUS and attempt < self._max_retries:
                await self._backoff(attempt)
                attempt += 1
                continue
            raise self._classify(response)

    async def get_json(self, path: str, params: Mapping[str, Any] | None = None) -> Any:  # noqa: ANN401 — a JSON document is Any by nature
        return (await self.get(path, params)).json()

    async def paginate(
        self, path: str, params: Mapping[str, Any] | None = None, *, max_pages: int = 20
    ) -> AsyncIterator[Any]:
        """Yield items across ``Link: rel="next"`` pages, up to ``max_pages``."""
        url: str | None = path
        query: Mapping[str, Any] | None = params
        for _ in range(max_pages):
            if url is None:
                return
            response = await self.get(url, query)
            for item in response.json():
                yield item
            url, query = _next_link(response), None

    @property
    def rate_limit_remaining(self) -> int | None:
        if self.last_response is None:
            return None
        value = self.last_response.headers.get("x-ratelimit-remaining")
        return int(value) if value and value.isdigit() else None

    async def _backoff(self, attempt: int) -> None:
        # Full jitter: a random wait up to the exponential ceiling, so many workers
        # retrying the same outage spread out instead of arriving together.
        ceiling = min(_BACKOFF_CAP_SECONDS, _BACKOFF_BASE_SECONDS * (2**attempt))
        await self._sleep(random.uniform(0, ceiling))  # noqa: S311 — jitter, not crypto

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        """A short wait the provider asked for (secondary rate limits), else None.

        An exhausted hourly allowance is not retried: the wait can be an hour.
        """
        if response.status_code not in (403, 429):
            return None
        if response.headers.get("x-ratelimit-remaining") == "0":
            return None
        value = response.headers.get("retry-after")
        if value is None or not value.isdigit():
            return None
        return min(float(value), _MAX_RETRY_AFTER_SECONDS)

    @staticmethod
    def _classify(response: httpx.Response) -> ProviderError:
        status = response.status_code
        error: ProviderError
        if status == 401:  # noqa: PLR2004
            error = CredentialRejected("The provider rejected the stored token.")
        elif status in (403, 429) and response.headers.get("x-ratelimit-remaining") == "0":
            error = RateLimitExhausted("The provider's hourly request allowance is used up.")
        elif status == 403:  # noqa: PLR2004
            error = AccessDenied("The token does not have the permission this needs.")
        elif status == 404:  # noqa: PLR2004
            error = NotFoundError("The provider has no such resource for this token.")
        else:
            error = ProviderUnavailable(f"The provider answered with an error ({status}).")
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            error.provider_message = str(body.get("message", ""))
        return error
