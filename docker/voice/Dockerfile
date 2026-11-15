# Local voice for the assistant (plan, F14): Whisper to listen, Kokoro to speak. CPU, no GPU.
# The models are not in the image: they are downloaded once to a volume (see docker/voice/README.md)
# so the image stays small and the model can be changed. For the offline delivery (F9) the volume
# is prepared beforehand with a connection.
FROM python:3.12-slim

# av 17 or later removed an argument that faster-whisper 1.2.1 still uses when reading the audio
# (TypeError: open() got an unexpected keyword argument 'metadata_errors'). 15 and 16 work.
RUN pip install --no-cache-dir "faster-whisper==1.2.1" "av>=15,<17" "pydantic>=2.9"

# Output voice (Kokoro-82M, ONNX on CPU). `espeakng-loader` brings the phonemizer: apt is not needed.
# The weights (326 MB) and the voices (28 MB) go in a volume, not in the image (see README).
RUN pip install --no-cache-dir "kokoro-onnx==0.6.1"

ENV HF_HOME=/models \
    SPACEAPP_KOKORO_DIR=/kokoro \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Voice HTTP service: Whisper (hearing) and Kokoro (speech). The repo is mounted at /app (see README).
EXPOSE 9000
CMD ["python", "-m", "spaceapp.devtools.voice_server"]
