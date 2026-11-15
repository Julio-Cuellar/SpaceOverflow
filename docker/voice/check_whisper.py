"""Checks the real Whisper inside the spaceapp-voice image (see docker/voice/README.md).

Without arguments it generates a tone and silence: it only proves the model loads and how long it takes.
Given audio paths (wav or webm) it transcribes them and shows text, confidence and time.
"""

import io
import math
import struct
import sys
import time
import wave
from pathlib import Path

from spaceapp.modules.assistant.adapters.outbound.whisper import (
    build_speech_to_text,
)


def wav_bytes(seconds, freq=None):
    rate = 16000
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(rate * seconds):
            v = int(8000 * math.sin(2 * math.pi * freq * i / rate)) if freq else 0
            frames += struct.pack("<h", v)
        w.writeframes(bytes(frames))
    return buf.getvalue()


stt = build_speech_to_text("small")
print("adapter:", type(stt).__name__, "available =", stt.available)

if sys.argv[1:]:
    for name in sys.argv[1:]:
        path = Path(name)
        kind = "audio/webm" if path.suffix == ".webm" else "audio/wav"
        t = time.time()
        r = stt.transcribe(path.read_bytes(), kind)
        print(f"{path.name}: {time.time() - t:.2f} s -> {r}")
    raise SystemExit

t = time.time()
r = stt.transcribe(wav_bytes(5, 440), "audio/wav")
print("1st transcription (loads the model):", round(time.time() - t, 1), "s ->", r)
t = time.time()
r = stt.transcribe(wav_bytes(5), "audio/wav")
print("2nd, 5 s of silence:", round(time.time() - t, 2), "s ->", r)
t = time.time()
r = stt.transcribe(wav_bytes(10, 300), "audio/wav")
print("3rd, 10 s of tone:", round(time.time() - t, 2), "s ->", r)
