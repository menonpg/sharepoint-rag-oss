# SharePoint RAG Indexer (OSS)

A vendor-neutral tool that indexes **any** Microsoft SharePoint site into a
retrieval-augmented-generation (RAG) knowledge base — then lets you query it in
natural language.

**🌐 [Website](https://menonpg.github.io/sharepoint-rag-oss/)** · [Setup guide](SETUP.md) · [Roadmap](ROADMAP.md)

It connects to SharePoint headlessly (app-only Microsoft Graph auth), performs
incremental **delta sync** so only changed files are reprocessed, extracts and
chunks document content, embeds it with a pluggable embedding backend, stores
vectors in a pluggable vector store, and answers questions with a pluggable LLM.

The default backends use **Azure OpenAI** (`text-embedding-3-large` for vectors,
`gpt-5-chat` for answers) and a **local** JSON/NumPy vector store — so you can run
the whole pipeline on a laptop with no cloud infrastructure.

---

## Why this exists

Most SharePoint-to-RAG pipelines are welded to one company's internal index and
identity stack. This project extracts the ~80% that is genuinely reusable —
Graph delta sync, content mirroring, change lifecycle tracking — and puts the
vendor-specific pieces (embeddings, vector store, LLM) behind clean interfaces.

```
SharePoint ──Graph delta──▶ Extract ──▶ Chunk ──▶ Embed ──▶ Vector Store
                                                                  │
                                        Question ──▶ Retrieve ──▶ LLM ──▶ Answer
```

## Features

- **Headless auth** — Microsoft Graph app-only (client credentials via MSAL).
- **Incremental delta sync** — folder-scoped Graph delta API with expired-cursor
  (HTTP 410) auto-reset. Only changed files are reprocessed.
- **Change lifecycle** — detects create / update / rename / move / delete and
  content-hash dedupe via a local state store.
- **Multi-format extraction** — PDF, DOCX, PPTX, HTML, Markdown, and plain text.
- **Pluggable backends** — swap embeddings, vector store, or LLM without touching
  the pipeline.
- **No cloud required** — local state + local vector store out of the box.
- **CLI first** — `init`, `sync`, `query`, `status`.

## Install

```bash
cd sharepoint-rag-oss
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
```

## Configure

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

You need two things:

1. **An Entra ID (Azure AD) app registration** with the Graph application
   permission `Sites.Read.All` (or `Files.Read.All`), admin-consented. Put its
   `client_id`, `client_secret`, and `tenant_id` in `.env`.
2. **Azure OpenAI** deployments for embeddings and chat (already scaffolded in
   `.env.example`).

> New to this? Follow the click-by-click walkthrough in [SETUP.md](SETUP.md) —
> it covers getting an admin tenant, registering the app, granting consent, and
> running your first index.

> Security: `.env` is gitignored. Never commit real keys. Rotate any key that has
> been shared in plaintext before publishing.

## Usage

```bash
# 1. Resolve and cache the target site/drive/folder ids
sp-rag init --site-url "https://contoso.sharepoint.com/sites/Research" \
            --folder "/Shared Documents/Knowledge Base"

# 2. Pull changes and index them (run this on a schedule / cron)
sp-rag sync

# 3. Ask questions
sp-rag query "What is our data retention policy for clinical trials?"

# Inspect state
sp-rag status
```

## Architecture

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Auth | `graph/auth.py` | MSAL app-only token, retry/backoff |
| Graph | `graph/client.py`, `graph/drive.py` | Request wrapper, site/drive/folder resolution |
| Delta | `graph/delta.py` | Folder-scoped delta sync + 410 reset |
| Extract | `ingest/extractor.py` | Bytes → text per file type |
| Chunk | `ingest/chunker.py` | Token-aware overlapping chunks |
| Embed | `embeddings/*` | `EmbeddingBackend` interface + Azure OpenAI impl |
| Store | `vectorstore/*` | `VectorStore` interface + local impl |
| LLM | `llm/*` | `ChatBackend` interface + Azure OpenAI impl |
| RAG | `rag/query.py` | Retrieve + prompt + answer |
| State | `state/store.py` | Delta links, per-file hashes, lifecycle |
| Pipeline | `ingest/pipeline.py` | Orchestrates sync end to end |

To add a backend (e.g. OpenAI, Cohere, pgvector, Pinecone, ILIAD), implement the
relevant interface and register it in `config.py`.

## Testing

The suite mocks Microsoft Graph and Azure at the interface boundary, so it runs
fully offline — no network, no SharePoint tenant, no Azure keys.

```bash
# With pytest (after: pip install -e ".[dev,all]")
pytest

# Or with zero third-party packages, using only the standard library:
python -m unittest discover -s tests -t .
```

Coverage includes: delta sync + expired-cursor (410) reset, content extraction,
token chunking with overlap, the incremental sync pipeline (create / update /
skip-unchanged / delete), retrieval + answer assembly, the local vector store,
and the CLI. Tests needing `numpy` (the local vector store) skip automatically
when it is not installed.

## License

MIT — see [LICENSE](LICENSE).
