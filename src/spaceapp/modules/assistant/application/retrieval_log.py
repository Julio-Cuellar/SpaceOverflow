"""Lo que el agente recuperó en cada turno. De aquí salen las citas, no del modelo.

Un turno se abre al empezar la consulta y se cierra al terminar o al agotarse el tiempo. Solo un
turno abierto acepta llamadas de las herramientas, así que el identificador del turno hace de
credencial de un solo uso y un resultado tardío no llega a ninguna respuesta.
"""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Sequence
from uuid import UUID

from spaceapp.platform.vocab import Citation


class TurnClosedError(LookupError):
    """El turno no está abierto: no existe, ya terminó o se cortó por tiempo."""


def passage_id(citation: Citation) -> str:
    raw = f"{citation.document_code}|{citation.requirement_ref}|{citation.page}|{citation.excerpt}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


class RetrievalLog:
    def __init__(self) -> None:
        self._turns: dict[UUID, dict[str, Citation]] = {}
        self._lock = threading.Lock()

    def open(self, turn_id: UUID) -> None:
        with self._lock:
            self._turns[turn_id] = {}

    def is_open(self, turn_id: UUID) -> bool:
        with self._lock:
            return turn_id in self._turns

    def record(self, turn_id: UUID, passages: Sequence[Citation]) -> list[str]:
        """Anota lo recuperado y devuelve los ids que verá el agente."""
        with self._lock:
            seen = self._turns.get(turn_id)
            if seen is None:
                raise TurnClosedError(str(turn_id))
            ids = []
            for citation in passages:
                identifier = passage_id(citation)
                seen.setdefault(identifier, citation)
                ids.append(identifier)
            return ids

    def retrieved(self, turn_id: UUID) -> list[Citation]:
        with self._lock:
            return list(self._turns.get(turn_id, {}).values())

    def close(self, turn_id: UUID) -> None:
        with self._lock:
            self._turns.pop(turn_id, None)
