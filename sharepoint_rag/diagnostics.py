"""Connectivity diagnostics for the ``sp-rag doctor`` command.

Validates auth, site/folder resolution, and read access without indexing
anything — the fastest way to confirm an Entra app registration and its
permissions are set up correctly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .config import Config
from .graph.client import GraphClient
from .graph.drive import list_children, resolve_target


@dataclass
class DoctorReport:
    token_acquired: bool = False
    site_id: Optional[str] = None
    drive_id: Optional[str] = None
    root_item_id: Optional[str] = None
    sample_files: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return (
            self.error is None
            and self.token_acquired
            and self.drive_id is not None
        )


def run_doctor(
    config: Config, site_url: str, folder: str, sample: int = 10
) -> DoctorReport:
    """Run staged connectivity checks and return a structured report.

    Each stage records partial progress so a failure pinpoints exactly where
    setup is incomplete (auth vs. permissions/site vs. listing).
    """
    report = DoctorReport()

    try:
        client = GraphClient(config.graph)
        report.token_acquired = True
    except Exception as exc:  # noqa: BLE001 - surface as a report, not a crash
        report.error = f"authentication failed: {exc}"
        return report

    try:
        target = resolve_target(client, site_url, folder)
        report.site_id = target.site_id
        report.drive_id = target.drive_id
        report.root_item_id = target.root_item_id
    except Exception as exc:  # noqa: BLE001
        report.error = f"site/folder resolution failed: {exc}"
        return report

    try:
        children = list_children(
            client, target.drive_id, target.root_item_id, top=sample
        )
        report.sample_files = [
            c.get("name", "?") for c in children if "file" in c
        ]
    except Exception as exc:  # noqa: BLE001
        report.error = f"listing folder contents failed: {exc}"

    return report
