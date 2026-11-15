# Whisper local para la voz del asistente (plan, F14). CPU, sin GPU.
# El modelo no va en la imagen: se baja una vez a un volumen (ver docker/voice/README.md) para que
# la imagen sea pequeña y el modelo se pueda cambiar. Para la entrega sin internet (F9) el volumen
# se prepara antes con conexión.
FROM python:3.12-slim

# av 17 o posterior quitó un argumento que faster-whisper 1.2.1 todavía usa al leer el audio
# (TypeError: open() got an unexpected keyword argument 'metadata_errors'). 15 y 16 funcionan.
RUN pip install --no-cache-dir "faster-whisper==1.2.1" "av>=15,<17" "pydantic>=2.9"

ENV HF_HOME=/models \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1

WORKDIR /app
