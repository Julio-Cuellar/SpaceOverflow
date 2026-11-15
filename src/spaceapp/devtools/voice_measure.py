"""Mide Whisper con grabaciones reales: error de palabras (WER) y tiempo de cada frase.

Cada grabación `data/voice/samples/<nombre>.wav` (o `.webm`) lleva al lado `<nombre>.txt` con lo que
se dijo. El servicio de voz debe estar en marcha (`docker/voice/README.md`).

    arecord -f S16_LE -r 16000 -c 1 -d 5 data/voice/samples/cabin.wav
    echo "What is the minimum cabin pressure?" > data/voice/samples/cabin.txt
    python -m spaceapp.devtools.voice_measure
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
import urllib.request
from collections.abc import Sequence
from pathlib import Path

_WORD = re.compile(r"[a-z0-9']+")


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def word_error_rate(expected: str, transcript: str) -> float:
    """Palabras que hay que cambiar, quitar o añadir (Levenshtein) entre las palabras esperadas."""
    reference = _words(expected)
    if not reference:
        raise ValueError("el texto esperado no tiene palabras")
    heard = _words(transcript)
    previous = list(range(len(heard) + 1))
    for i, word in enumerate(reference, start=1):
        current = [i]
        for j, other in enumerate(heard, start=1):
            cost = 0 if word == other else 1
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost))
        previous = current
    return previous[-1] / len(reference)


def measure(results: Sequence[tuple[str, str, float]]) -> dict[str, float]:
    """Resumen de `(esperado, transcrito, segundos)`."""
    errors = [word_error_rate(expected, heard) for expected, heard, _ in results]
    seconds = [elapsed for _, _, elapsed in results]
    return {
        "samples": len(results),
        "mean_wer": statistics.fmean(errors),
        "mean_seconds": statistics.fmean(seconds),
        "max_seconds": max(seconds),
    }


def _transcribe(url: str, path: Path) -> tuple[str, float]:
    content_type = "audio/webm" if path.suffix == ".webm" else "audio/wav"
    request = urllib.request.Request(
        f"{url.rstrip('/')}/transcribe",
        data=path.read_bytes(),
        headers={"Content-Type": content_type},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=300) as response:
        text = json.load(response)["text"]
    return text, time.perf_counter() - started


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mide la transcripción con grabaciones reales.")
    parser.add_argument("--samples", type=Path, default=Path("data/voice/samples"))
    parser.add_argument("--url", default="http://127.0.0.1:9000")
    args = parser.parse_args(argv)

    audio = sorted([*args.samples.glob("*.wav"), *args.samples.glob("*.webm")])
    pairs = [
        (path, path.with_suffix(".txt")) for path in audio if path.with_suffix(".txt").exists()
    ]
    if not pairs:
        print(f"No hay grabaciones con su .txt en {args.samples}", flush=True)
        return 2

    results: list[tuple[str, str, float]] = []
    for path, text_path in pairs:
        expected = text_path.read_text(encoding="utf-8").strip()
        heard, elapsed = _transcribe(args.url, path)
        results.append((expected, heard, elapsed))
        print(f"{path.name}: {elapsed:5.1f} s  WER {word_error_rate(expected, heard):4.0%}")
        print(f"   dicho:      {expected}\n   transcrito: {heard}")
    summary = measure(results)
    print(
        f"\n{summary['samples']:.0f} frases · WER medio {summary['mean_wer']:.0%} · "
        f"{summary['mean_seconds']:.1f} s de media, {summary['max_seconds']:.1f} s el máximo"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
