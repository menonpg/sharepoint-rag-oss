"""Command-line interface: init, sync, query, status."""

from __future__ import annotations

import argparse
import sys

from .config import Config
from .diagnostics import run_doctor
from .ingest.pipeline import init_target, run_sync
from .rag import answer_question
from .state import StateStore


def _cmd_init(args: argparse.Namespace) -> int:
    config = Config.load()
    print(f"Resolving {args.site_url} :: {args.folder or '(root)'} ...")
    init_target(config, args.site_url, args.folder or "")
    print("Target saved. Run 'sp-rag sync' to index.")
    return 0


def _cmd_sync(args: argparse.Namespace) -> int:
    config = Config.load()
    print("Syncing changes from SharePoint ...")
    report = run_sync(config)
    if report.delta_reset:
        print("(delta cursor expired — performed a full folder rescan)")
    print(
        f"Done. processed={report.processed} skipped={report.skipped} "
        f"deleted={report.deleted} errors={report.errors}"
    )
    return 0 if report.errors == 0 else 1


def _cmd_query(args: argparse.Namespace) -> int:
    config = Config.load()
    result = answer_question(config, args.question)
    print("\n" + result.text + "\n")
    if result.sources:
        print("Sources:")
        for src in sorted(result.sources, key=lambda s: -s.score):
            print(f"  - {src.file_name}  (score={src.score:.3f})")
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    config = Config.load()
    site_url = args.site_url
    folder = args.folder
    if not site_url:
        store = StateStore(config.home / "state.json")
        site_url = store.state.site_url
        folder = store.state.folder_path or ""
        if not site_url:
            print(
                "No --site-url given and no saved target. "
                "Run 'sp-rag init' first or pass --site-url.",
                file=sys.stderr,
            )
            return 1

    print(f"Checking access to {site_url} :: {folder or '(root)'} ...\n")
    report = run_doctor(config, site_url, folder)

    print(f"Token acquired:  {'yes' if report.token_acquired else 'no'}")
    if report.site_id:
        print(f"Site id:         {report.site_id}")
    if report.drive_id:
        print(f"Drive id:        {report.drive_id}")
    if report.root_item_id:
        print(f"Folder item id:  {report.root_item_id}")
    if report.sample_files:
        print(f"Visible files (first {len(report.sample_files)}):")
        for name in report.sample_files:
            print(f"  - {name}")

    if report.error:
        print(f"\nFAILED: {report.error}", file=sys.stderr)
        return 1

    print("\nAll checks passed. You're ready to run 'sp-rag sync'.")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    config = Config.load()
    store = StateStore(config.home / "state.json")
    state = store.state
    print(f"Home:        {config.home}")
    print(f"Site:        {state.site_url or '(not initialized)'}")
    print(f"Folder:      {state.folder_path or '(root)'}")
    print(f"Drive id:    {state.drive_id or '-'}")
    print(f"Delta link:  {'set' if state.delta_link else 'none (full scan pending)'}")
    print(f"Files known: {len(state.files)}")
    print(f"Indexed:     {store.indexed_count()}")
    print(f"Embeddings:  {config.embedding_backend}")
    print(f"Vector store:{config.vector_store}")
    print(f"Chat:        {config.chat_backend}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sp-rag",
        description="Index any SharePoint site into a RAG knowledge base and query it.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Resolve and cache a target site/folder.")
    p_init.add_argument("--site-url", required=True, help="https://host/sites/Name")
    p_init.add_argument("--folder", default="", help="Drive-relative folder path.")
    p_init.set_defaults(func=_cmd_init)

    p_sync = sub.add_parser("sync", help="Pull changes and index them.")
    p_sync.set_defaults(func=_cmd_sync)

    p_query = sub.add_parser("query", help="Ask a question over the index.")
    p_query.add_argument("question", help="Natural language question.")
    p_query.set_defaults(func=_cmd_query)

    p_status = sub.add_parser("status", help="Show index and target status.")
    p_status.set_defaults(func=_cmd_status)

    p_doctor = sub.add_parser(
        "doctor", help="Test auth + read access without indexing anything."
    )
    p_doctor.add_argument(
        "--site-url", default=None, help="Override; defaults to the saved target."
    )
    p_doctor.add_argument(
        "--folder", default="", help="Drive-relative folder path."
    )
    p_doctor.set_defaults(func=_cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001 - CLI boundary: report cleanly
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
