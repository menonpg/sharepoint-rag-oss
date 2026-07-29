import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sharepoint_rag import diagnostics as diag_mod
from sharepoint_rag.diagnostics import run_doctor
from sharepoint_rag.graph.drive import DriveTarget

from tests.fakes import make_config


class DiagnosticsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.config = make_config(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def _target(self):
        return DriveTarget(
            site_id="site1",
            drive_id="drive1",
            root_item_id="root1",
            site_url="https://h/sites/X",
            folder_path="Docs",
        )

    def test_auth_failure_stops_early(self):
        def boom(_creds):
            raise RuntimeError("invalid_client")

        with mock.patch.object(diag_mod, "GraphClient", boom):
            report = run_doctor(self.config, "https://h/sites/X", "Docs")

        self.assertFalse(report.token_acquired)
        self.assertIn("authentication failed", report.error)
        self.assertFalse(report.ok)

    def test_site_resolution_failure(self):
        with mock.patch.object(diag_mod, "GraphClient", lambda c: object()), \
            mock.patch.object(
                diag_mod, "resolve_target", side_effect=RuntimeError("HTTP 403")
            ):
            report = run_doctor(self.config, "https://h/sites/X", "Docs")

        self.assertTrue(report.token_acquired)
        self.assertIsNone(report.drive_id)
        self.assertIn("site/folder resolution failed", report.error)
        self.assertFalse(report.ok)

    def test_happy_path_lists_files(self):
        children = [
            {"name": "a.pdf", "file": {}},
            {"name": "b.docx", "file": {}},
            {"name": "Subfolder", "folder": {}},
        ]
        with mock.patch.object(diag_mod, "GraphClient", lambda c: object()), \
            mock.patch.object(diag_mod, "resolve_target", return_value=self._target()), \
            mock.patch.object(diag_mod, "list_children", return_value=children):
            report = run_doctor(self.config, "https://h/sites/X", "Docs")

        self.assertTrue(report.ok)
        self.assertEqual(report.drive_id, "drive1")
        self.assertEqual(report.sample_files, ["a.pdf", "b.docx"])  # folder excluded

    def test_listing_failure_is_reported_but_keeps_ids(self):
        with mock.patch.object(diag_mod, "GraphClient", lambda c: object()), \
            mock.patch.object(diag_mod, "resolve_target", return_value=self._target()), \
            mock.patch.object(
                diag_mod, "list_children", side_effect=RuntimeError("HTTP 500")
            ):
            report = run_doctor(self.config, "https://h/sites/X", "Docs")

        self.assertEqual(report.drive_id, "drive1")
        self.assertIn("listing folder contents failed", report.error)
        self.assertFalse(report.ok)


if __name__ == "__main__":
    unittest.main()
