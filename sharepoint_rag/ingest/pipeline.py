"""End-to-end sync pipeline: Graph delta -> extract -> chunk -> embed -> store.

Idempotent and incremental: uses the saved delta link so only changed items are
processed, and content hashing so unchanged files are skipped even after a
delta reset.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..config import Config
from ..embeddings import build_embedding_backend
from ..graph.client import GraphClient
from ..graph.delta import download_item_content, get_changes
from ..graph.drive import resolve_target
from ..state import FileState, StateStore
from ..vectorstore import VectorRecord, build_vector_store
from .chunker import chunk_text
from .extractor import extract_text, is_supported
from .time_utils import utc_now_iso


@dataclass
class SyncReport:
    processed: int = 0
    skipped: int = 0
    deleted: int = 0
    errors: int = 0
    delta_reset: bool = False


def init_target(config: Config, site_url: str, folder_path: str) -> None:
    """Resolve and persist the target site/drive/folder for future syncs."""
    client = GraphClient(config.graph)
    target = resolve_target(client, site_url, folder_path)

    store = StateStore(config.home / "state.json")
    store.state.site_url = target.site_url
    store.state.folder_path = target.folder_path
    store.state.site_id = target.site_id
    store.state.drive_id = target.drive_id
    store.state.root_item_id = target.root_item_id
    store.state.delta_link = None  # force a full scan on next sync
    store.save()


def run_sync(config: Config) -> SyncReport:
    state_store = StateStore(config.home / "state.json")
    state = state_store.state

    if not state.drive_id or not state.root_item_id:
        raise RuntimeError("Target not initialized. Run 'sp-rag init' first.")

    client = GraphClient(config.graph)
    embedder = build_embedding_backend(config)
    vectors = build_vector_store(config)

    result = get_changes(
        client, state.drive_id, state.root_item_id, state.delta_link
    )
    report = SyncReport(delta_reset=result.was_reset)

    for item in result.changed_items:
        try:
            _process_item(
                item, config, client, embedder, vectors, state_store, report
            )
        except Exception as exc:  # noqa: BLE001 - keep syncing other items
            report.errors += 1
            print(f"Error processing item {item.get('id')}: {exc}")

    state.delta_link = result.new_delta_link
    state_store.save()
    return report


def _process_item(
    item: dict,
    config: Config,
    client: GraphClient,
    embedder,
    vectors,
    state_store: StateStore,
    report: SyncReport,
) -> None:
    file_id = item["id"]

    # Deletion tombstone.
    if "deleted" in item:
        vectors.delete_by_file(file_id)
        existing = state_store.get_file(file_id)
        if existing:
            existing.status = "deleted"
            existing.updated_at = utc_now_iso()
            state_store.put_file(existing)
        report.deleted += 1
        return

    # Folders carry no content.
    if "folder" in item or "file" not in item:
        report.skipped += 1
        return

    name = item.get("name", "")
    if not is_supported(name):
        report.skipped += 1
        return

    path = _item_path(item)

    data = download_item_content(client, state_store.state.drive_id, file_id)
    content_hash = hashlib.sha256(data).hexdigest()

    existing = state_store.get_file(file_id)
    if existing and existing.content_hash == content_hash and existing.status == "indexed":
        report.skipped += 1
        return

    text = extract_text(name, data)
    if not text.strip():
        report.skipped += 1
        return

    # Replace prior chunks for this file (handles updates and renames).
    vectors.delete_by_file(file_id)

    chunks = chunk_text(
        text,
        chunk_size_tokens=config.chunk_size_tokens,
        overlap_tokens=config.chunk_overlap_tokens,
    )
    embeddings = embedder.embed([c.text for c in chunks])

    records = [
        VectorRecord(
            id=f"{file_id}::{chunk.index}",
            vector=vector,
            text=chunk.text,
            metadata={
                "file_id": file_id,
                "file_name": name,
                "path": path,
                "chunk_index": chunk.index,
            },
        )
        for chunk, vector in zip(chunks, embeddings)
    ]
    vectors.upsert(records)

    state_store.put_file(
        FileState(
            file_id=file_id,
            name=name,
            path=path,
            content_hash=content_hash,
            status="indexed",
            updated_at=utc_now_iso(),
        )
    )
    state_store.save()
    report.processed += 1


def _item_path(item: dict) -> str:
    parent = item.get("parentReference", {})
    parent_path = parent.get("path", "")
    name = item.get("name", "")
    if parent_path:
        return f"{parent_path}/{name}"
    return name
