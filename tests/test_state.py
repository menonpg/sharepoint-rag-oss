import tempfile
import unittest
from pathlib import Path

from sharepoint_rag.state import FileState, StateStore


class StateStoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "state.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_empty_state_defaults(self):
        store = StateStore(self.path)
        self.assertIsNone(store.state.delta_link)
        self.assertEqual(store.state.files, {})
        self.assertEqual(store.indexed_count(), 0)

    def test_put_get_and_persist(self):
        store = StateStore(self.path)
        store.state.site_url = "https://host/sites/X"
        store.state.drive_id = "drive1"
        store.put_file(
            FileState(
                file_id="f1",
                name="a.txt",
                path="/a.txt",
                content_hash="hash1",
                status="indexed",
                updated_at="2026-01-01T00:00:00+00:00",
            )
        )
        store.save()

        reloaded = StateStore(self.path)
        self.assertEqual(reloaded.state.site_url, "https://host/sites/X")
        self.assertEqual(reloaded.state.drive_id, "drive1")
        f = reloaded.get_file("f1")
        self.assertIsNotNone(f)
        self.assertEqual(f.content_hash, "hash1")
        self.assertEqual(reloaded.indexed_count(), 1)

    def test_remove_file(self):
        store = StateStore(self.path)
        store.put_file(
            FileState("f1", "a", "/a", "h", "indexed", "2026-01-01T00:00:00+00:00")
        )
        store.remove_file("f1")
        self.assertIsNone(store.get_file("f1"))

    def test_indexed_count_ignores_deleted(self):
        store = StateStore(self.path)
        store.put_file(FileState("f1", "a", "/a", "h", "indexed", "t"))
        store.put_file(FileState("f2", "b", "/b", "h", "deleted", "t"))
        self.assertEqual(store.indexed_count(), 1)


if __name__ == "__main__":
    unittest.main()
