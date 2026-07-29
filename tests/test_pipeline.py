import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sharepoint_rag.ingest import pipeline as pipeline_mod
from sharepoint_rag.ingest.pipeline import run_sync
from sharepoint_rag.graph.delta import DeltaResult
from sharepoint_rag.state import StateStore

from tests.fakes import (
    FakeEmbeddingBackend,
    InMemoryVectorStore,
    deleted_item,
    file_item,
    folder_item,
    make_config,
)


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.config = make_config(self.home)
        self.store = InMemoryVectorStore()

        # Seed a target so run_sync doesn't bail out.
        state = StateStore(self.home / "state.json")
        state.state.drive_id = "drive1"
        state.state.root_item_id = "root1"
        state.save()

        # Content served per item id.
        self.content = {
            "f1": b"alpha beta gamma delta epsilon",
            "f2": b"one two three four five six",
        }

    def tearDown(self):
        self._tmp.cleanup()

    def _patches(self, delta_result):
        return [
            mock.patch.object(pipeline_mod, "GraphClient", lambda creds: object()),
            mock.patch.object(
                pipeline_mod, "get_changes", lambda *a, **k: delta_result
            ),
            mock.patch.object(
                pipeline_mod,
                "download_item_content",
                lambda client, drive_id, item_id: self.content.get(item_id, b""),
            ),
            mock.patch.object(
                pipeline_mod, "build_embedding_backend", lambda cfg: FakeEmbeddingBackend()
            ),
            mock.patch.object(
                pipeline_mod, "build_vector_store", lambda cfg: self.store
            ),
        ]

    def _run(self, delta_result):
        patches = self._patches(delta_result)
        for p in patches:
            p.start()
        try:
            return run_sync(self.config)
        finally:
            for p in patches:
                p.stop()

    def test_indexes_new_files_and_skips_folders(self):
        delta = DeltaResult(
            changed_items=[
                folder_item("fold1", "Subfolder"),
                file_item("f1", "a.txt"),
                file_item("f2", "b.txt"),
                file_item("f3", "image.png"),  # unsupported
            ],
            new_delta_link="https://delta/1",
            was_reset=False,
        )
        report = self._run(delta)
        self.assertEqual(report.processed, 2)
        self.assertGreaterEqual(report.skipped, 2)  # folder + png
        self.assertGreater(self.store.count(), 0)

        # delta link persisted
        state = StateStore(self.home / "state.json")
        self.assertEqual(state.state.delta_link, "https://delta/1")
        self.assertEqual(state.indexed_count(), 2)

    def test_unchanged_file_is_skipped_on_resync(self):
        delta = DeltaResult(
            changed_items=[file_item("f1", "a.txt")],
            new_delta_link="d1",
            was_reset=False,
        )
        first = self._run(delta)
        self.assertEqual(first.processed, 1)

        # Same content again -> hash match -> skipped.
        delta2 = DeltaResult(
            changed_items=[file_item("f1", "a.txt")],
            new_delta_link="d2",
            was_reset=False,
        )
        second = self._run(delta2)
        self.assertEqual(second.processed, 0)
        self.assertEqual(second.skipped, 1)

    def test_changed_content_reindexes(self):
        self._run(
            DeltaResult([file_item("f1", "a.txt")], "d1", False)
        )
        count_before = self.store.count()

        self.content["f1"] = b"completely different words now here"
        report = self._run(
            DeltaResult([file_item("f1", "a.txt")], "d2", False)
        )
        self.assertEqual(report.processed, 1)
        # old chunks replaced, not duplicated
        ids = {r.metadata["file_id"] for r in self.store._records.values()}
        self.assertEqual(ids, {"f1"})
        self.assertGreaterEqual(self.store.count(), 1)
        self.assertGreater(count_before, 0)

    def test_deletion_removes_vectors(self):
        self._run(DeltaResult([file_item("f1", "a.txt")], "d1", False))
        self.assertGreater(self.store.count(), 0)

        report = self._run(DeltaResult([deleted_item("f1")], "d2", False))
        self.assertEqual(report.deleted, 1)
        self.assertEqual(self.store.count(), 0)

        state = StateStore(self.home / "state.json")
        self.assertEqual(state.get_file("f1").status, "deleted")

    def test_uninitialized_target_raises(self):
        empty_home = Path(self._tmp.name) / "empty"
        empty_home.mkdir()
        cfg = make_config(empty_home)
        with self.assertRaises(RuntimeError):
            run_sync(cfg)


if __name__ == "__main__":
    unittest.main()
