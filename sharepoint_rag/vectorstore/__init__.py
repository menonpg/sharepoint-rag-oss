"""Vector store backends: interface + registry."""

from __future__ import annotations

from ..config import Config
from .base import VectorRecord, VectorStore


def build_vector_store(config: Config) -> VectorStore:
    if config.vector_store == "local":
        from .local import LocalVectorStore

        return LocalVectorStore(config.home / "vectors.json")

    raise ValueError(f"Unknown vector store: {config.vector_store}")


__all__ = ["VectorRecord", "VectorStore", "build_vector_store"]
