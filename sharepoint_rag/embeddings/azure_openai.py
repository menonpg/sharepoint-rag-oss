"""Azure OpenAI embedding backend (text-embedding-3-large by default)."""

from __future__ import annotations

from ..config import AzureBackendConfig
from .base import EmbeddingBackend

# text-embedding-3-large native dimensionality.
_DEFAULT_DIMENSIONS = 3072
_BATCH = 64


class AzureOpenAIEmbeddings(EmbeddingBackend):
    def __init__(self, cfg: AzureBackendConfig):
        try:
            from openai import AzureOpenAI
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "openai required: pip install 'sharepoint-rag-oss[azure]'"
            ) from exc

        self._client = AzureOpenAI(
            azure_endpoint=cfg.endpoint,
            api_key=cfg.api_key,
            api_version=cfg.api_version,
        )
        self._deployment = cfg.deployment
        self._dims = _DEFAULT_DIMENSIONS

    @property
    def dimensions(self) -> int:
        return self._dims

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _BATCH):
            batch = texts[start : start + _BATCH]
            resp = self._client.embeddings.create(
                model=self._deployment, input=batch
            )
            ordered = sorted(resp.data, key=lambda d: d.index)
            for item in ordered:
                vectors.append(item.embedding)
        if vectors:
            self._dims = len(vectors[0])
        return vectors
