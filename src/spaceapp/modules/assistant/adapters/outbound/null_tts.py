"""Null output-voice adapter: without a service, the answer is read on screen and all goes on."""

from __future__ import annotations


class NullTextToSpeech:
    available = False

    def speak(self, text: str) -> bytes | None:
        return None
