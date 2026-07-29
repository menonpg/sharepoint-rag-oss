"""Abstract embedding backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingBackend(ABC):
    """Turns text into dense vectors. Implement this to add a provider."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        ...

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, preserving order."""
        ...

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
