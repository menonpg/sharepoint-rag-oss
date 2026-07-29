"""Local JSON state store.

Tracks the target, the Graph delta link, and per-file lifecycle (content hash,
last status) so sync is incremental and idempotent. This is the OSS analogue of
the DynamoDB state machine in a cloud deployment.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FileState:
    file_id: str
    name: str
    path: str
    content_hash: str
    status: str  # indexed | deleted | error
    updated_at: str


@dataclass
class State:
    site_url: Optional[str] = None
    folder_path: Optional[str] = None
    site_id: Optional[str] = None
    drive_id: Optional[str] = None
    root_item_id: Optional[str] = None
    delta_link: Optional[str] = None
    files: dict[str, dict] = field(default_factory=dict)


class StateStore:
    def __init__(self, path: Path):
        self._path = Path(path)
        self.state = self._load()

    def _load(self) -> State:
        if not self._path.exists():
            return State()
        raw = json.loads(self._path.read_text())
        return State(
            site_url=raw.get("site_url"),
            folder_path=raw.get("folder_path"),
            site_id=raw.get("site_id"),
            drive_id=raw.get("drive_id"),
            root_item_id=raw.get("root_item_id"),
            delta_link=raw.get("delta_link"),
            files=raw.get("files", {}),
        )

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self.state), indent=2))
        tmp.replace(self._path)

    # --- file lifecycle -------------------------------------------------
    def get_file(self, file_id: str) -> Optional[FileState]:
        raw = self.state.files.get(file_id)
        return FileState(**raw) if raw else None

    def put_file(self, file_state: FileState) -> None:
        self.state.files[file_state.file_id] = asdict(file_state)

    def remove_file(self, file_id: str) -> None:
        self.state.files.pop(file_id, None)

    def indexed_count(self) -> int:
        return sum(1 for f in self.state.files.values() if f.get("status") == "indexed")
