"""In-memory fakes implementing the real backend interfaces.

These let the full pipeline and RAG flow be tested without Microsoft Graph,
Azure OpenAI, numpy, or any network access.
"""

from __future__ import annotations

import math
from pathlib import Path

from sharepoint_rag.config import AzureBackendConfig, Config, GraphCreds
from sharepoint_rag.embeddings.base import EmbeddingBackend
from sharepoint_rag.llm.base import ChatBackend, ChatMessage
from sharepoint_rag.vectorstore.base import SearchHit, VectorRecord, VectorStore


# --------------------------------------------------------------------------
# Graph fakes
# --------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeGraphClient:
    """Returns queued responses in order, ignoring the URL."""

    def __init__(self, responses: list[FakeResponse]):
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []
        self.access_token = "fake-token"

    def request(self, method, url, **kwargs) -> FakeResponse:
        self.calls.append((method, url))
        if not self._responses:
            raise AssertionError("FakeGraphClient ran out of queued responses")
        return self._responses.pop(0)


# --------------------------------------------------------------------------
# Embedding fake
# --------------------------------------------------------------------------
class FakeEmbeddingBackend(EmbeddingBackend):
    """Deterministic, dependency-free embeddings.

    Maps each text to a fixed-length vector using a stable hash over words, so
    similar texts (sharing words) get similar vectors.
    """

    _DIMS = 16

    @property
    def dimensions(self) -> int:
        return self._DIMS

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vec = [0.0] * self._DIMS
            for word in text.lower().split():
                vec[hash(word) % self._DIMS] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


# --------------------------------------------------------------------------
# Vector store fake (pure Python cosine, no numpy)
# --------------------------------------------------------------------------
class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self._records: dict[str, VectorRecord] = {}

    def upsert(self, records: list[VectorRecord]) -> None:
        for rec in records:
            self._records[rec.id] = rec

    def delete_by_file(self, file_id: str) -> None:
        for rid in [
            rid
            for rid, rec in self._records.items()
            if rec.metadata.get("file_id") == file_id
        ]:
            del self._records[rid]

    def search(self, query_vector, top_k):
        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a)) or 1e-10
            nb = math.sqrt(sum(y * y for y in b)) or 1e-10
            return dot / (na * nb)

        scored = [
            SearchHit(record=rec, score=cosine(query_vector, rec.vector))
            for rec in self._records.values()
        ]
        scored.sort(key=lambda h: -h.score)
        return scored[:top_k]

    def count(self) -> int:
        return len(self._records)


# --------------------------------------------------------------------------
# Chat fake
# --------------------------------------------------------------------------
class FakeChatBackend(ChatBackend):
    def __init__(self):
        self.last_messages: list[ChatMessage] = []

    def complete(self, messages: list[ChatMessage], max_tokens: int = 1024) -> str:
        self.last_messages = messages
        user = next((m for m in reversed(messages) if m.role == "user"), None)
        return f"ANSWER based on context. (q-len={len(user.content) if user else 0})"


# --------------------------------------------------------------------------
# Config factory
# --------------------------------------------------------------------------
def make_config(home: Path) -> Config:
    return Config(
        graph=GraphCreds(tenant_id="t", client_id="c", client_secret="s"),
        home=Path(home),
        embedding_backend="fake",
        chat_backend="fake",
        vector_store="memory",
        azure_embedding=None,
        azure_chat=None,
        chunk_size_tokens=800,
        chunk_overlap_tokens=120,
        retrieval_top_k=6,
    )


# --------------------------------------------------------------------------
# Graph drive item builders
# --------------------------------------------------------------------------
def file_item(item_id: str, name: str, parent_path: str = "/drive/root:") -> dict:
    return {
        "id": item_id,
        "name": name,
        "file": {"mimeType": "text/plain"},
        "parentReference": {"path": parent_path},
    }


def folder_item(item_id: str, name: str) -> dict:
    return {"id": item_id, "name": name, "folder": {"childCount": 0}}


def deleted_item(item_id: str) -> dict:
    return {"id": item_id, "deleted": {"state": "deleted"}}
