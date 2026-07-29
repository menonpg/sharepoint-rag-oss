"""Abstract vector store interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class VectorRecord:
    id: str
    vector: list[float]
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchHit:
    record: VectorRecord
    score: float


class VectorStore(ABC):
    """Persist and search embedding vectors. Implement this to add a backend."""

    @abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None:
        ...

    @abstractmethod
    def delete_by_file(self, file_id: str) -> None:
        """Remove all chunks belonging to a source file."""
        ...

    @abstractmethod
    def search(self, query_vector: list[float], top_k: int) -> list["SearchHit"]:
        ...

    @abstractmethod
    def count(self) -> int:
        ...
