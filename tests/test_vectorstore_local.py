import tempfile
import unittest
from pathlib import Path

from sharepoint_rag.vectorstore.base import VectorRecord

try:
    import numpy  # noqa: F401

    from sharepoint_rag.vectorstore.local import LocalVectorStore

    HAVE_NUMPY = True
except ImportError:  # numpy not installed
    HAVE_NUMPY = False


@unittest.skipUnless(HAVE_NUMPY, "numpy not installed")
class LocalVectorStoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "vectors.json"

    def tearDown(self):
        self._tmp.cleanup()

    def _rec(self, rid, vec, file_id="f1"):
        return VectorRecord(
            id=rid, vector=vec, text=rid, metadata={"file_id": file_id}
        )

    def test_upsert_search_and_persist(self):
        store = LocalVectorStore(self.path)
        store.upsert(
            [
                self._rec("a", [1.0, 0.0, 0.0]),
                self._rec("b", [0.0, 1.0, 0.0]),
            ]
        )
        hits = store.search([1.0, 0.0, 0.0], top_k=1)
        self.assertEqual(hits[0].record.id, "a")
        self.assertAlmostEqual(hits[0].score, 1.0, places=5)

        # persisted to disk and reloadable
        reloaded = LocalVectorStore(self.path)
        self.assertEqual(reloaded.count(), 2)

    def test_delete_by_file(self):
        store = LocalVectorStore(self.path)
        store.upsert(
            [
                self._rec("a", [1.0, 0.0], file_id="f1"),
                self._rec("b", [0.0, 1.0], file_id="f2"),
            ]
        )
        store.delete_by_file("f1")
        self.assertEqual(store.count(), 1)
        self.assertEqual(store.search([0.0, 1.0], 1)[0].record.id, "b")

    def test_search_empty_store(self):
        store = LocalVectorStore(self.path)
        self.assertEqual(store.search([1.0, 0.0], 3), [])

    def test_upsert_overwrites_same_id(self):
        store = LocalVectorStore(self.path)
        store.upsert([self._rec("a", [1.0, 0.0])])
        store.upsert([self._rec("a", [0.0, 1.0])])
        self.assertEqual(store.count(), 1)


if __name__ == "__main__":
    unittest.main()
