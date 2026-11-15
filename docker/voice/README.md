# Local voice (assistant)

Voice HTTP service in Docker: Whisper (hearing: audio → text, `HttpSpeechToText`) and Kokoro-82M (speech: text → audio, `HttpTextToSpeech`). It is the same `WhisperSpeechToText` adapter (`faster-whisper`, CPU, `int8`) without installing anything in the team's Python. The models live in volumes, not in the image.

## Setup (once, with internet)

```bash
docker build -t spaceapp-voice:dev docker/voice          # image of about 876 MB
docker volume create spaceapp-whisper-models
docker run --rm -v spaceapp-whisper-models:/models spaceapp-voice:dev \
  python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
```

The model is `Systran/faster-whisper-small` (MIT, about 464 MB in the volume). It takes about 30 s to download; afterwards it loads in 1 to 2 s.

## Output voice: Kokoro-82M (once, with internet)

Kokoro-82M (Apache-2.0) runs on CPU with `kokoro-onnx` 0.6.1 (MIT), which is already in the image (`espeakng-loader` brings the phonemizer: apt is not needed). The weights go in a separate volume, like Whisper's:

```bash
docker volume create spaceapp-kokoro-models
docker run --rm -v spaceapp-kokoro-models:/kokoro spaceapp-voice:dev python -c "
import urllib.request
base = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'
for name in ('voices-v1.0.bin', 'kokoro-v1.0.onnx'):      # 28.2 MB and 325.5 MB
    urllib.request.urlretrieve(base + name, '/kokoro/' + name)"
```

Voice `af_heart`, US English (`kokoro.py`). Without the files the service still starts with the null voice and `/speak` answers 503.

## Service (offline)

```bash
docker run -d --name spaceapp-voice --restart unless-stopped -p 127.0.0.1:9000:9000 \
  -v spaceapp-whisper-models:/models:ro -v spaceapp-kokoro-models:/kokoro:ro \
  -v "$PWD":/app:ro -e HF_HUB_OFFLINE=1 spaceapp-voice:dev
curl -s localhost:9000/health                                   # {"status": "ok"}
curl -s -X POST localhost:9000/transcribe -H 'Content-Type: audio/wav' --data-binary @phrase.wav
curl -s -X POST localhost:9000/speak -H 'Content-Type: application/json' -d '{"text":"Hello."}' -o hello.wav
```

The repo is mounted at `/app` (read-only): the service runs `spaceapp.devtools.voice_server`, which uses the language (English) and the context text of `whisper.py`. The model loads on the first request (≈ 2 s). With both models loaded the container uses about 1.1 GB; Docker Desktop shares 4 GB among this one, Ollama and n8n.

The development server calls it at `SPACEAPP_WHISPER_URL` (default `http://127.0.0.1:9000`). If it does not answer, the voice says to type the question. The audio is deleted as soon as it is transcribed.

## Measuring with real voice

```bash
mkdir -p data/voice/samples
arecord -f S16_LE -r 16000 -c 1 -d 5 data/voice/samples/cabin.wav     # say the phrase and wait 5 s
echo "What is the minimum cabin pressure?" > data/voice/samples/cabin.txt
.venv/bin/python -m spaceapp.devtools.voice_measure
```

For each phrase it prints what was said and what was transcribed, with its word error rate (WER) and time, and the average at the end. `data/voice/` is not versioned: these are recordings of people.

## Model check (offline)

```bash
docker run --rm -v spaceapp-whisper-models:/models:ro -v "$PWD":/app:ro -e HF_HUB_OFFLINE=1 \
  spaceapp-voice:dev python /app/docker/voice/check_whisper.py
```

Without arguments it generates tone and silence: it proves the model loads and how long it takes, **not** the accuracy. Measuring accuracy needs voice recordings:

```bash
mkdir -p data/voice/samples
arecord -f S16_LE -r 16000 -c 1 -d 6 data/voice/samples/hypoxia.wav     # say a phrase and wait 6 s
docker run --rm -v spaceapp-whisper-models:/models:ro -v "$PWD":/app:ro -e HF_HUB_OFFLINE=1 \
  spaceapp-voice:dev python /app/docker/voice/check_whisper.py /app/data/voice/samples/hypoxia.wav
```

## Why `av` is pinned

`faster-whisper` 1.2.1 calls `av.open(..., metadata_errors="ignore")`. `av` 17 or later removed that argument and the transcription fails with `TypeError: open() got an unexpected keyword argument 'metadata_errors'`. With `av` 15 and 16 it works (13.1.0 too). The `Dockerfile` pins `av>=15,<17`. If `faster-whisper` is installed outside Docker it must be pinned the same way.

## Limits

- **Memory:** Docker Desktop gives all containers 4 GB. With Ollama loaded (llama 2.3 GB + bge-m3 1.2 GB) the VM runs out of memory and the kernel kills the voice container (exit 137, `OOMKilled`). `--restart unless-stopped` brings it back, but the fix is to raise the Docker Desktop memory (Settings → Resources) to 8 GB, or to use a smaller Whisper model.
- Whisper can repeat its own context text when the audio has no clear speech (hallucination); there is no guard yet.
- For the offline delivery (F9) the model volumes must be prepared beforehand with a connection.
