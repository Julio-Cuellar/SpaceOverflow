"""Comando de ingesta: `python -m spaceapp.modules.knowledge.ingest`.

Lee el manifiesto, extrae el texto de los PDFs que haya en la carpeta y guarda los fragmentos
en un archivo JSONL. Funciona sin internet; no descarga nada.
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
    """Escribe el índice nuevo aparte y lo pone en su lugar de una vez."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.unlink(missing_ok=True)
    JsonlChunkStore(temporary).add(chunks)
    temporary.replace(path)


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
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="descarta el índice anterior; úsalo si cambiaron las reglas de corte",
    )
    args = parser.parse_args(argv)

    try:
        entries = load_manifest(args.manifest)
    except ManifestError as error:
        print(f"Manifiesto inválido: {error}", file=sys.stderr)
        return 2

    # Al reconstruir se indexa en memoria y solo se reemplaza el archivo si algo se indexó:
    # una reconstrucción sin PDFs a mano no debe dejar el índice vacío.
    store = InMemoryChunkStore() if args.rebuild else JsonlChunkStore(args.out)
    report = ingest_manifest(entries, args.pdf_dir, store, include_optional=args.include_optional)
    if args.rebuild and report.ingested:
        _replace_index(args.out, store.all())
    elif args.rebuild:
        print(f"No se indexó nada: se conserva el índice anterior en {args.out}", file=sys.stderr)

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
