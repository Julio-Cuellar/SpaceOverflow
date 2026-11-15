"""What the agent retrieved in each turn. The citations come from here, not from the model.

A turn opens when the query starts and closes when it ends or the time runs out. Only an open turn
accepts calls from the tools, so the turn identifier works as a single-use credential and a late
result does not reach any answer.
"""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Sequence
from uuid import UUID

from spaceapp.platform.vocab import Citation


class TurnClosedError(LookupError):
    """The turn is not open: it does not exist, already ended or was cut by timeout."""


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
        """Records what was retrieved and returns the ids the agent will see."""
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
