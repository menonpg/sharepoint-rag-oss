"""Resolve SharePoint site URLs to Graph site / drive / folder item ids."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import quote, urlparse

from ..config import GRAPH_BASE_URL

if TYPE_CHECKING:
    from .client import GraphClient


@dataclass
class DriveTarget:
    """Everything needed to run a folder-scoped delta query."""

    site_id: str
    drive_id: str
    root_item_id: str
    site_url: str
    folder_path: str


def resolve_site_id(client: GraphClient, site_url: str) -> str:
    """Resolve a SharePoint site URL (https://host/sites/Name) to a Graph site id."""
    parsed = urlparse(site_url)
    host = parsed.netloc
    server_relative = parsed.path.rstrip("/")
    url = f"{GRAPH_BASE_URL}/sites/{host}:{server_relative}"
    resp = client.request("GET", url)
    resp.raise_for_status()
    return resp.json()["id"]


def resolve_default_drive_id(client: GraphClient, site_id: str) -> str:
    url = f"{GRAPH_BASE_URL}/sites/{site_id}/drive"
    resp = client.request("GET", url)
    resp.raise_for_status()
    return resp.json()["id"]


def resolve_folder_item_id(client: GraphClient, drive_id: str, folder_path: str) -> str:
    """Resolve a drive-relative folder path to its item id.

    An empty path (or "/") resolves to the drive root.
    """
    clean = folder_path.strip().strip("/")
    if not clean:
        url = f"{GRAPH_BASE_URL}/drives/{drive_id}/root"
    else:
        encoded = quote(clean)
        url = f"{GRAPH_BASE_URL}/drives/{drive_id}/root:/{encoded}"
    resp = client.request("GET", url)
    resp.raise_for_status()
    return resp.json()["id"]


def resolve_target(
    client: GraphClient, site_url: str, folder_path: str
) -> DriveTarget:
    """Resolve a site URL + folder path into a fully-qualified DriveTarget."""
    site_id = resolve_site_id(client, site_url)
    drive_id = resolve_default_drive_id(client, site_id)
    root_item_id = resolve_folder_item_id(client, drive_id, folder_path)
    return DriveTarget(
        site_id=site_id,
        drive_id=drive_id,
        root_item_id=root_item_id,
        site_url=site_url,
        folder_path=folder_path,
    )


def list_children(
    client: "GraphClient", drive_id: str, item_id: str, top: int = 10
) -> list[dict]:
    """List up to ``top`` direct children of a drive item (files and folders)."""
    url = f"{GRAPH_BASE_URL}/drives/{drive_id}/items/{item_id}/children?$top={top}"
    resp = client.request("GET", url)
    resp.raise_for_status()
    return resp.json().get("value", [])
