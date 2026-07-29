"""Retrieval-augmented question answering over the indexed vector store."""

from __future__ import annotations

from dataclasses import dataclass

from .embeddings import build_embedding_backend
from .config import Config
from .llm import ChatMessage, build_chat_backend
from .vectorstore import build_vector_store

_SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions using only the provided "
    "SharePoint document context. If the answer is not in the context, say you "
    "don't know. Cite the source file names you used."
)


@dataclass
class Source:
    file_name: str
    path: str
    score: float


@dataclass
class Answer:
    text: str
    sources: list[Source]


def answer_question(config: Config, question: str) -> Answer:
    embedder = build_embedding_backend(config)
    store = build_vector_store(config)
    chat = build_chat_backend(config)

    query_vector = embedder.embed_one(question)
    hits = store.search(query_vector, config.retrieval_top_k)

    if not hits:
        return Answer(text="No documents have been indexed yet.", sources=[])

    context_blocks = []
    sources: list[Source] = []
    for hit in hits:
        meta = hit.record.metadata
        name = meta.get("file_name", "unknown")
        context_blocks.append(f"[Source: {name}]\n{hit.record.text}")
        sources.append(
            Source(file_name=name, path=meta.get("path", ""), score=hit.score)
        )

    context = "\n\n---\n\n".join(context_blocks)
    messages = [
        ChatMessage(role="system", content=_SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=f"Context:\n{context}\n\nQuestion: {question}",
        ),
    ]
    text = chat.complete(messages)

    # Deduplicate sources by file name, keeping best score.
    best: dict[str, Source] = {}
    for src in sources:
        if src.file_name not in best or src.score > best[src.file_name].score:
            best[src.file_name] = src

    return Answer(text=text, sources=list(best.values()))
