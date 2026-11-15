# Whisper local (voz del asistente)

Servicio HTTP de Whisper en Docker: el backend le manda el audio y recibe el texto (`HttpSpeechToText`). Es el mismo adaptador `WhisperSpeechToText` (`faster-whisper`, CPU, `int8`) sin instalar nada en el Python del equipo. El modelo vive en un volumen, no en la imagen.

## Preparación (una vez, con internet)

```bash
docker build -t spaceapp-voice:dev docker/voice          # imagen de unos 840 MB
docker volume create spaceapp-whisper-models
docker run --rm -v spaceapp-whisper-models:/models spaceapp-voice:dev \
  python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
```

El modelo es `Systran/faster-whisper-small` (MIT, unos 464 MB en el volumen). Tarda unos 30 s en bajar; después carga en 1 a 2 s.

## Servicio (sin internet)

```bash
docker run -d --name spaceapp-voice -p 127.0.0.1:9000:9000 \
  -v spaceapp-whisper-models:/models:ro -v "$PWD":/app:ro -e HF_HUB_OFFLINE=1 spaceapp-voice:dev
curl -s localhost:9000/health                                   # {"status": "ok"}
curl -s -X POST localhost:9000/transcribe -H 'Content-Type: audio/wav' --data-binary @frase.wav
```

La repo se monta en `/app` (solo lectura): el servicio ejecuta `spaceapp.devtools.voice_server`, que usa el idioma (inglés) y el texto de contexto de `whisper.py`. El modelo carga en la primera petición (≈ 2 s). Con el modelo cargado, el contenedor usa unos 300 MB; Docker Desktop reparte 4 GB entre este, Ollama y n8n.

El servidor de desarrollo lo llama en `SPACEAPP_WHISPER_URL` (por defecto `http://127.0.0.1:9000`). Si no responde, la voz dice que se escriba la pregunta. El audio se borra en cuanto se transcribe.

## Medir con voz real

```bash
mkdir -p data/voice/samples
arecord -f S16_LE -r 16000 -c 1 -d 5 data/voice/samples/cabin.wav     # di la frase y espera 5 s
echo "What is the minimum cabin pressure?" > data/voice/samples/cabin.txt
.venv/bin/python -m spaceapp.devtools.voice_measure
```

Imprime, por frase, lo dicho y lo transcrito con su tasa de error de palabras (WER) y el tiempo, y al final la media. `data/voice/` no se versiona: son grabaciones de personas.

## Comprobación del modelo (sin internet)

```bash
docker run --rm -v spaceapp-whisper-models:/models:ro -v "$PWD":/app:ro -e HF_HUB_OFFLINE=1 \
  spaceapp-voice:dev python /app/docker/voice/check_whisper.py
```

Sin argumentos genera tono y silencio: prueba que el modelo carga y cuánto tarda, **no** la precisión. Para medir la precisión hacen falta grabaciones de voz:

```bash
mkdir -p data/voice/samples
arecord -f S16_LE -r 16000 -c 1 -d 6 data/voice/samples/hipoxia.wav     # di una frase y espera 6 s
docker run --rm -v spaceapp-whisper-models:/models:ro -v "$PWD":/app:ro -e HF_HUB_OFFLINE=1 \
  spaceapp-voice:dev python /app/docker/voice/check_whisper.py /app/data/voice/samples/hipoxia.wav
```

`data/voice/` no se versiona: son grabaciones de personas.

## Por qué `av` está fijado

`faster-whisper` 1.2.1 llama a `av.open(..., metadata_errors="ignore")`. `av` 17 o posterior quitó ese argumento y la transcripción falla con `TypeError: open() got an unexpected keyword argument 'metadata_errors'`. Con `av` 15 y 16 funciona (13.1.0 también). El `Dockerfile` fija `av>=15,<17`. Si se instala `faster-whisper` fuera de Docker hay que fijarlo igual.

## Límites

- No se ha medido la precisión con voz real ni con ruido de cabina (no había grabaciones).
- Para la entrega sin internet (F9) el volumen del modelo hay que prepararlo antes con conexión.
