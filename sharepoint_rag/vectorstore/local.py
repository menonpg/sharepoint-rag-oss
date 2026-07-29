"""Local JSON + NumPy vector store.

Zero-infrastructure default: persists records to a JSON file and does cosine
similarity search in memory with NumPy. Suitable for thousands to low tens of
thousands of chunks. Swap in pgvector/Pinecone/FAISS for production scale.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .base import SearchHit, VectorRecord, VectorStore


class LocalVectorStore(VectorStore):
    def __init__(self, path: Path):
        self._path = Path(path)
        self._records: dict[str, VectorRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        raw = json.loads(self._path.read_text())
        for item in raw:
            rec = VectorRecord(
                id=item["id"],
                vector=item["vector"],
                text=item["text"],
                metadata=item.get("metadata", {}),
            )
            self._records[rec.id] = rec

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "id": r.id,
                "vector": r.vector,
                "text": r.text,
                "metadata": r.metadata,
            }
            for r in self._records.values()
        ]
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload))
        tmp.replace(self._path)

    def upsert(self, records: list[VectorRecord]) -> None:
        for rec in records:
            self._records[rec.id] = rec
        self._save()

    def delete_by_file(self, file_id: str) -> None:
        to_remove = [
            rid
            for rid, rec in self._records.items()
            if rec.metadata.get("file_id") == file_id
        ]
        for rid in to_remove:
            del self._records[rid]
        if to_remove:
            self._save()

    def search(self, query_vector: list[float], top_k: int) -> list[SearchHit]:
        if not self._records:
            return []

        ids = list(self._records.keys())
        matrix = np.array([self._records[i].vector for i in ids], dtype=np.float32)
        query = np.array(query_vector, dtype=np.float32)

        matrix_norms = np.linalg.norm(matrix, axis=1)
        query_norm = np.linalg.norm(query)
        denom = matrix_norms * query_norm
        denom[denom == 0] = 1e-10

        scores = (matrix @ query) / denom
        order = np.argsort(-scores)[:top_k]

        return [
            SearchHit(record=self._records[ids[i]], score=float(scores[i]))
            for i in order
        ]

    def count(self) -> int:
        return len(self._records)
