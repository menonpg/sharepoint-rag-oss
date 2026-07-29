"""Chat/LLM backends: interface + registry."""

from __future__ import annotations

from ..config import Config
from .base import ChatBackend, ChatMessage


def build_chat_backend(config: Config) -> ChatBackend:
    if config.chat_backend == "azure_openai":
        from .azure_openai import AzureOpenAIChat

        if config.azure_chat is None:
            raise RuntimeError("Azure chat config missing.")
        return AzureOpenAIChat(config.azure_chat)

    raise ValueError(f"Unknown chat backend: {config.chat_backend}")


__all__ = ["ChatBackend", "ChatMessage", "build_chat_backend"]
