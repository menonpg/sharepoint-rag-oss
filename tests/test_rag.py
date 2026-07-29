import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sharepoint_rag import rag as rag_mod
from sharepoint_rag.rag import answer_question
from sharepoint_rag.vectorstore.base import VectorRecord

from tests.fakes import (
    FakeChatBackend,
    FakeEmbeddingBackend,
    InMemoryVectorStore,
    make_config,
)


class RagTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.config = make_config(Path(self._tmp.name))
        self.embedder = FakeEmbeddingBackend()
        self.store = InMemoryVectorStore()
        self.chat = FakeChatBackend()

    def tearDown(self):
        self._tmp.cleanup()

    def _seed(self):
        docs = {
            "policy.txt": "data retention policy clinical trials seven years",
            "menu.txt": "cafeteria lunch menu pizza salad soup",
        }
        for name, text in docs.items():
            vec = self.embedder.embed_one(text)
            self.store.upsert(
                [
                    VectorRecord(
                        id=f"{name}::0",
                        vector=vec,
                        text=text,
                        metadata={"file_id": name, "file_name": name, "path": f"/{name}"},
                    )
                ]
            )

    def _patched_answer(self, question):
        patches = [
            mock.patch.object(rag_mod, "build_embedding_backend", lambda c: self.embedder),
            mock.patch.object(rag_mod, "build_vector_store", lambda c: self.store),
            mock.patch.object(rag_mod, "build_chat_backend", lambda c: self.chat),
        ]
        for p in patches:
            p.start()
        try:
            return answer_question(self.config, question)
        finally:
            for p in patches:
                p.stop()

    def test_empty_index_returns_message(self):
        result = self._patched_answer("anything")
        self.assertIn("No documents", result.text)
        self.assertEqual(result.sources, [])

    def test_retrieves_relevant_source(self):
        self._seed()
        result = self._patched_answer("what is our data retention policy")
        self.assertTrue(result.sources)
        top = max(result.sources, key=lambda s: s.score)
        self.assertEqual(top.file_name, "policy.txt")

    def test_context_passed_to_chat(self):
        self._seed()
        self._patched_answer("data retention")
        user_msg = [m for m in self.chat.last_messages if m.role == "user"][0]
        self.assertIn("Context:", user_msg.content)
        self.assertIn("data retention", user_msg.content)

    def test_sources_are_deduplicated(self):
        self._seed()
        # add a second chunk of the same file
        vec = self.embedder.embed_one("more retention policy text")
        self.store.upsert(
            [
                VectorRecord(
                    id="policy.txt::1",
                    vector=vec,
                    text="more retention policy text",
                    metadata={
                        "file_id": "policy.txt",
                        "file_name": "policy.txt",
                        "path": "/policy.txt",
                    },
                )
            ]
        )
        result = self._patched_answer("retention policy")
        names = [s.file_name for s in result.sources]
        self.assertEqual(len(names), len(set(names)), "sources should be unique by file")


if __name__ == "__main__":
    unittest.main()
