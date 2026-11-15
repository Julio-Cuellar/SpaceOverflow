"""Adaptador nulo de voz: sin modelo, la tripulación escribe la pregunta y todo sigue igual."""

from __future__ import annotations

from spaceapp.modules.assistant.domain.voice import Transcript


class NullSpeechToText:
    available = False

    def transcribe(self, audio: bytes, content_type: str) -> Transcript | None:
        return None
