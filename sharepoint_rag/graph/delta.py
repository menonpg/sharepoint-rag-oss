"""Folder-scoped Microsoft Graph delta sync.

Returns only items that changed since the last saved delta link. On HTTP 410
(expired/invalid cursor) the sync resets to a fresh full folder scan, matching
Graph's documented recovery behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..config import GRAPH_BASE_URL

if TYPE_CHECKING:
    from .client import GraphClient


@dataclass
class DeltaResult:
    changed_items: list[dict]
    new_delta_link: str
    was_reset: bool


def get_changes(
    client: GraphClient,
    drive_id: str,
    root_item_id: str,
    delta_link: str | None,
) -> DeltaResult:
    """Run a folder-scoped delta query.

    If ``delta_link`` is provided it is used verbatim (never parse the token
    manually). Otherwise a fresh delta enumeration of the folder subtree starts.
    """
    changed: list[dict] = []
    new_delta_link: str | None = None
    was_reset = False

    if delta_link:
        url = delta_link
    else:
        url = f"{GRAPH_BASE_URL}/drives/{drive_id}/items/{root_item_id}/delta"

    while url:
        resp = client.request("GET", url)

        if resp.status_code == 410:
            # Saved delta link expired: restart the folder-scoped delta query.
            was_reset = True
            changed = []
            url = f"{GRAPH_BASE_URL}/drives/{drive_id}/items/{root_item_id}/delta"
            resp = client.request("GET", url)

        resp.raise_for_status()
        data = resp.json()
        changed.extend(data.get("value", []))

        if "@odata.nextLink" in data:
            url = data["@odata.nextLink"]
        else:
            new_delta_link = data.get("@odata.deltaLink")
            url = None

    if not new_delta_link:
        raise RuntimeError(
            "Graph delta query completed without returning @odata.deltaLink."
        )

    return DeltaResult(changed, new_delta_link, was_reset)


def download_item_content(
    client: GraphClient, drive_id: str, item_id: str
) -> bytes:
    """Download the raw bytes of a drive item."""
    url = f"{GRAPH_BASE_URL}/drives/{drive_id}/items/{item_id}/content"
    resp = client.request("GET", url, stream=True)
    resp.raise_for_status()
    return resp.content
