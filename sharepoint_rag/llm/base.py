"""Abstract chat/LLM backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


class ChatBackend(ABC):
    """Generates a completion from a list of chat messages."""

    @abstractmethod
    def complete(self, messages: list[ChatMessage], max_tokens: int = 1024) -> str:
        ...
