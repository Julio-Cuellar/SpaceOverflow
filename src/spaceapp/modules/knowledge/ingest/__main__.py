"""Comando de ingesta: `python -m spaceapp.modules.knowledge.ingest`.

Lee el manifiesto, extrae el texto de los PDFs que haya en la carpeta y guarda los fragmentos
en un archivo JSONL. Funciona sin internet; no descarga nada.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from spaceapp.modules.knowledge.ingest.manifest import ManifestError, load_manifest
from spaceapp.modules.knowledge.ingest.pipeline import ingest_manifest
from spaceapp.modules.knowledge.ingest.store import JsonlChunkStore


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Indexa los PDFs de NASA como fragmentos citables."
    )
    parser.add_argument("--manifest", type=Path, default=Path("data/knowledge/manifest.json"))
    parser.add_argument("--pdf-dir", type=Path, default=Path("data/knowledge/pdfs"))
    parser.add_argument("--out", type=Path, default=Path("data/knowledge/index/chunks.jsonl"))
    parser.add_argument(
        "--include-optional", action="store_true", help="intenta también los documentos opcionales"
    )
    args = parser.parse_args(argv)

    try:
        entries = load_manifest(args.manifest)
    except ManifestError as error:
        print(f"Manifiesto inválido: {error}", file=sys.stderr)
        return 2

    report = ingest_manifest(
        entries, args.pdf_dir, JsonlChunkStore(args.out), include_optional=args.include_optional
    )

    print(f"Ingeridos: {', '.join(report.ingested) or 'ninguno'}")
    if report.missing:
        print(f"Sin PDF en {args.pdf_dir}: {', '.join(report.missing)}")
    if report.empty:
        print(f"Sin texto extraíble (¿escaneo?): {', '.join(report.empty)}")
    if report.failed:
        print(f"No se pudieron leer: {', '.join(report.failed)}")
    if report.skipped:
        print(f"Omitidos (opcionales o sin abrir): {', '.join(report.skipped)}")
    print(f"Fragmentos nuevos: {report.chunks_added}")
    return 0 if report.ingested else 1


if __name__ == "__main__":
    raise SystemExit(main())
