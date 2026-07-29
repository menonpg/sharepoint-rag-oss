"""Configuration loading and backend registry.

All secrets are read from the environment (optionally via a local ``.env`` file).
Nothing is hardcoded, so the package is safe to publish as open source.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional at runtime
    pass


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Copy .env.example to .env and fill it in."
        )
    return value


def _get(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass
class GraphCreds:
    tenant_id: str
    client_id: str
    client_secret: str

    @classmethod
    def from_env(cls) -> "GraphCreds":
        return cls(
            tenant_id=_require("SP_TENANT_ID"),
            client_id=_require("SP_CLIENT_ID"),
            client_secret=_require("SP_CLIENT_SECRET"),
        )


@dataclass
class AzureBackendConfig:
    endpoint: str
    api_key: str
    deployment: str
    api_version: str


@dataclass
class Config:
    graph: GraphCreds
    home: Path

    embedding_backend: str
    chat_backend: str
    vector_store: str

    azure_embedding: Optional[AzureBackendConfig]
    azure_chat: Optional[AzureBackendConfig]

    chunk_size_tokens: int = 800
    chunk_overlap_tokens: int = 120
    retrieval_top_k: int = 6

    extra: dict = field(default_factory=dict)

    @classmethod
    def load(cls) -> "Config":
        home = Path(_get("SP_RAG_HOME", ".sp_rag")).expanduser().resolve()
        home.mkdir(parents=True, exist_ok=True)

        embedding_backend = _get("EMBEDDING_BACKEND", "azure_openai")
        chat_backend = _get("CHAT_BACKEND", "azure_openai")
        vector_store = _get("VECTOR_STORE", "local")

        azure_embedding = None
        if embedding_backend == "azure_openai":
            azure_embedding = AzureBackendConfig(
                endpoint=_require("AZURE_EMBEDDING_ENDPOINT"),
                api_key=_require("AZURE_EMBEDDING_API_KEY"),
                deployment=_require("AZURE_EMBEDDING_DEPLOYMENT"),
                api_version=_get("AZURE_EMBEDDING_API_VERSION", "2023-05-15"),
            )

        azure_chat = None
        if chat_backend == "azure_openai":
            azure_chat = AzureBackendConfig(
                endpoint=_require("AZURE_CHAT_ENDPOINT"),
                api_key=_require("AZURE_CHAT_API_KEY"),
                deployment=_require("AZURE_CHAT_DEPLOYMENT"),
                api_version=_get("AZURE_CHAT_API_VERSION", "2025-01-01-preview"),
            )

        return cls(
            graph=GraphCreds.from_env(),
            home=home,
            embedding_backend=embedding_backend,
            chat_backend=chat_backend,
            vector_store=vector_store,
            azure_embedding=azure_embedding,
            azure_chat=azure_chat,
            chunk_size_tokens=int(_get("CHUNK_SIZE_TOKENS", "800")),
            chunk_overlap_tokens=int(_get("CHUNK_OVERLAP_TOKENS", "120")),
            retrieval_top_k=int(_get("RETRIEVAL_TOP_K", "6")),
        )
