"""Comprueba el Whisper real dentro de la imagen spaceapp-voice (ver docker/voice/README.md).

Sin argumentos genera tono y silencio: solo prueba que el modelo carga y cuánto tarda.
Con rutas de audio (wav o webm) las transcribe y muestra texto, confianza y tiempo.
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
print("adaptador:", type(stt).__name__, "available =", stt.available)

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
print("1.ª transcripción (carga el modelo):", round(time.time() - t, 1), "s ->", r)
t = time.time()
r = stt.transcribe(wav_bytes(5), "audio/wav")
print("2.ª, 5 s de silencio:", round(time.time() - t, 2), "s ->", r)
t = time.time()
r = stt.transcribe(wav_bytes(10, 300), "audio/wav")
print("3.ª, 10 s de tono:", round(time.time() - t, 2), "s ->", r)
