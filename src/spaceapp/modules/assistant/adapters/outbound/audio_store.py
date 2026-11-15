"""Guarda el audio de la tripulación en una carpeta local. Nada sale de la nave."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID


class LocalAudioStore:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def save(self, utterance_id: UUID, audio: bytes, extension: str) -> str:
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._directory / f"{utterance_id}.{extension}"
        path.write_bytes(audio)
        return str(path)
