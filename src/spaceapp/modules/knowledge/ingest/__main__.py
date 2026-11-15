"""Ingestion command: `python -m spaceapp.modules.knowledge.ingest`.

Reads the manifest, extracts the text of the PDFs found in the folder and saves the chunks
in a JSONL file. It works without internet; it downloads nothing.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from spaceapp.modules.knowledge.ingest.chunking import Chunk
from spaceapp.modules.knowledge.ingest.manifest import ManifestError, load_manifest
from spaceapp.modules.knowledge.ingest.pipeline import ingest_manifest
from spaceapp.modules.knowledge.ingest.store import InMemoryChunkStore, JsonlChunkStore


def _replace_index(path: Path, chunks: list[Chunk]) -> None:
    """Writes the new index aside and moves it into place in one step."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.unlink(missing_ok=True)
    JsonlChunkStore(temporary).add(chunks)
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Indexes the NASA PDFs as citable chunks.")
    parser.add_argument("--manifest", type=Path, default=Path("data/knowledge/manifest.json"))
    parser.add_argument("--pdf-dir", type=Path, default=Path("data/knowledge/pdfs"))
    parser.add_argument("--out", type=Path, default=Path("data/knowledge/index/chunks.jsonl"))
    parser.add_argument(
        "--include-optional", action="store_true", help="also try the optional documents"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="discards the previous index; use it if the splitting rules changed",
    )
    args = parser.parse_args(argv)

    try:
        entries = load_manifest(args.manifest)
    except ManifestError as error:
        print(f"Invalid manifest: {error}", file=sys.stderr)
        return 2

    # A rebuild indexes in memory and replaces the file only if something was indexed:
    # a rebuild without hand-placed PDFs must not leave the index empty.
    store = InMemoryChunkStore() if args.rebuild else JsonlChunkStore(args.out)
    report = ingest_manifest(entries, args.pdf_dir, store, include_optional=args.include_optional)
    if args.rebuild and report.ingested:
        _replace_index(args.out, store.all())
    elif args.rebuild:
        print(f"Nothing was indexed: the previous index in {args.out} is kept", file=sys.stderr)

    print(f"Ingested: {', '.join(report.ingested) or 'none'}")
    if report.missing:
        print(f"No PDF in {args.pdf_dir}: {', '.join(report.missing)}")
    if report.empty:
        print(f"No extractable text (scan?): {', '.join(report.empty)}")
    if report.failed:
        print(f"Could not be read: {', '.join(report.failed)}")
    if report.skipped:
        print(f"Skipped (optional or unopened): {', '.join(report.skipped)}")
    print(f"New chunks: {report.chunks_added}")
    return 0 if report.ingested else 1


if __name__ == "__main__":
    raise SystemExit(main())
