"""Embedding backends: interface + registry."""

from __future__ import annotations

from ..config import Config
from .base import EmbeddingBackend


def build_embedding_backend(config: Config) -> EmbeddingBackend:
    if config.embedding_backend == "azure_openai":
        from .azure_openai import AzureOpenAIEmbeddings

        if config.azure_embedding is None:
            raise RuntimeError("Azure embedding config missing.")
        return AzureOpenAIEmbeddings(config.azure_embedding)

    raise ValueError(f"Unknown embedding backend: {config.embedding_backend}")


__all__ = ["EmbeddingBackend", "build_embedding_backend"]
