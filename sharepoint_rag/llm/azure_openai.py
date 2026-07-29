"""Azure OpenAI chat backend.

Note: gpt-5-chat uses ``max_completion_tokens`` rather than ``max_tokens``.
"""

from __future__ import annotations

from ..config import AzureBackendConfig
from .base import ChatBackend, ChatMessage


class AzureOpenAIChat(ChatBackend):
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

    def complete(self, messages: list[ChatMessage], max_tokens: int = 1024) -> str:
        resp = self._client.chat.completions.create(
            model=self._deployment,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            max_completion_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""
