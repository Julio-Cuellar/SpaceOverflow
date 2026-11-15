"""Null voice adapter: without a model, the crew types the question and all goes on the same."""

from __future__ import annotations

from spaceapp.modules.assistant.domain.voice import Transcript


class NullSpeechToText:
    available = False

    def transcribe(self, audio: bytes, content_type: str) -> Transcript | None:
        return None
