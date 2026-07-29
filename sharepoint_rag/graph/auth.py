"""App-only Microsoft Graph authentication using MSAL client credentials."""

from __future__ import annotations

import time

from ..config import GraphCreds

_NON_RETRYABLE = {
    "invalid_client",
    "invalid_grant",
    "unauthorized_client",
    "invalid_scope",
}

_RETRYABLE_TEXT = (
    "Connection reset by peer",
    "Connection aborted",
    "Max retries exceeded",
    "Read timed out",
    "ConnectTimeout",
    "ConnectionError",
    "ProtocolError",
    "Temporary failure",
    "NameResolutionError",
)


def acquire_token(creds: GraphCreds) -> str:
    """Acquire a Graph app-only access token, retrying transient failures.

    Retries network hiccups and transient MSAL responses with backoff, but fails
    fast on non-retryable credential errors (bad client id/secret/tenant).
    """

    import msal
    import requests

    sleep_schedule = [2, 5, 10]
    max_attempts = len(sleep_schedule) + 1
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            app = msal.ConfidentialClientApplication(
                client_id=creds.client_id,
                client_credential=creds.client_secret,
                authority=f"https://login.microsoftonline.com/{creds.tenant_id}",
            )
            result = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )

            if "access_token" in result:
                return result["access_token"]

            error = result.get("error", "")
            if error in _NON_RETRYABLE:
                raise RuntimeError(f"Failed to get Graph token: {result}")

            last_error = RuntimeError(f"Failed to get Graph token: {result}")

        except requests.exceptions.RequestException as exc:
            last_error = exc
        except Exception as exc:  # noqa: BLE001 - classify then re-raise
            if not any(text in str(exc) for text in _RETRYABLE_TEXT):
                raise
            last_error = exc

        if attempt < max_attempts:
            time.sleep(sleep_schedule[attempt - 1])

    raise RuntimeError(
        f"Failed to get Graph token after {max_attempts} attempts: {last_error}"
    )
