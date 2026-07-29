"""Thin Microsoft Graph HTTP client with retry, throttling, and 401 refresh."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from ..config import GraphCreds
from .auth import acquire_token

if TYPE_CHECKING:
    import requests

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 60


class GraphClient:
    """Wraps requests to Microsoft Graph.

    - Injects the bearer token on every call.
    - Retries 429 (throttling, honoring Retry-After) and 5xx transient errors.
    - Refreshes the token once if Graph returns 401.
    """

    def __init__(self, creds: GraphCreds):
        self._creds = creds
        self.access_token = acquire_token(creds)

    def refresh_token(self) -> None:
        self.access_token = acquire_token(self._creds)

    def request(
        self,
        method: str,
        url: str,
        *,
        stream: bool = False,
        timeout: tuple[int, int] | None = None,
        **kwargs: Any,
    ) -> "requests.Response":
        response = self._request_with_retry(
            method, url, stream=stream, timeout=timeout, **kwargs
        )
        if response.status_code == 401:
            self.refresh_token()
            response = self._request_with_retry(
                method, url, stream=stream, timeout=timeout, **kwargs
            )
        return response

    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        stream: bool = False,
        timeout: tuple[int, int] | None = None,
        **kwargs: Any,
    ) -> "requests.Response":
        import requests

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        timeout = timeout or (CONNECT_TIMEOUT, READ_TIMEOUT)

        backoff = [1, 2, 5, 10]
        for attempt in range(len(backoff) + 1):
            response = requests.request(
                method, url, headers=headers, stream=stream, timeout=timeout, **kwargs
            )

            if response.status_code == 429 or response.status_code >= 500:
                if attempt == len(backoff):
                    return response
                retry_after = response.headers.get("Retry-After")
                wait = int(retry_after) if retry_after else backoff[attempt]
                time.sleep(wait)
                continue

            return response

        return response  # pragma: no cover
