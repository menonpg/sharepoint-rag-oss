# Roadmap

Current release: **v0.1** — a lean, vendor-neutral SharePoint → RAG indexer with
pluggable embedding, vector, and LLM backends; local vector store; incremental
delta sync; and a CLI (`init`, `sync`, `query`, `status`, `doctor`).

The items below are planned, not yet shipped.

## v0.2 — Memory + RAG/RLM via soul.py

Integrate [soul.py](https://github.com/menonpg/soul.py) as the retrieval and
memory layer on top of this indexer. This project handles ingestion
(SharePoint → chunks → vectors); soul.py handles retrieval strategy and
persistent memory. They compose cleanly:

- **Knowledge base = the SharePoint index.** Feed the indexed corpus to soul.py's
  `HybridAgent` as its `knowledge_dir` / vector source.
- **RAG + RLM query router.** soul.py auto-routes focused queries to fast vector
  RAG and exhaustive queries to RLM (recursive synthesis) — better multi-hop and
  temporal reasoning than RAG alone.
- **Per-user memory.** soul.py's `MEMORY.md` gives the agent persistent
  conversational memory alongside the document knowledge base.
- **Shared stack.** soul.py already supports **Azure embeddings + Qdrant**,
  matching this project's default Azure OpenAI configuration.

Deliverable: an optional `sharepoint_rag/agents/soul_adapter.py` plus a
`sp-rag chat` command that runs a soul.py `HybridAgent` over the indexed corpus.
Kept behind an optional extra (`pip install '.[soul]'`) so the core stays lean.

## v0.2 — Production vector backends

Additional `VectorStore` implementations behind the existing interface:

- **Qdrant** (aligns with soul.py; managed or self-hosted).
- **pgvector** (Postgres) for teams already running Postgres.
- **Pinecone** for fully managed scale.

## v0.3 — Permissions-aware retrieval

Mirror SharePoint ACLs into the index (the DELOS pipeline this was extracted from
does this) so answers only surface content a given user is allowed to see.

## v0.3 — Scale & operations

- **Sites.Selected** onboarding helper (scope the app to one site).
- Webhook-driven near-real-time sync (Graph change notifications) in addition to
  scheduled delta scans.
- Optional serverless deployment (container / Lambda) for hands-off indexing.

## Backlog

- Incremental re-embedding on chunker/config changes.
- OCR for scanned PDFs and image content.
- A managed/hosted option for non-technical teams.

Contributions welcome — open an issue to discuss before large changes.
