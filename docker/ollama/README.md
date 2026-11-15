# Local Ollama (assistant model)

Ollama in Docker for the n8n agent. The model lives in a volume. Everything runs locally, without internet once downloaded.

## Setup (once, with internet)

```bash
docker pull ollama/ollama:latest                    # 3.4 GB compressed; about 8.5 GB on disk
docker volume create spaceapp-ollama-models
docker run -d --name spaceapp-ollama -v spaceapp-ollama-models:/root/.ollama \
  -p 127.0.0.1:11434:11434 ollama/ollama:latest
docker exec spaceapp-ollama ollama pull llama3.2:3b   # 2.0 GB
docker cp docker/ollama/Modelfile spaceapp-ollama:/tmp/Modelfile
docker exec spaceapp-ollama ollama create spaceapp-asistente -f /tmp/Modelfile   # downloads nothing
```

n8n (in another container) reaches it at `http://host.docker.internal:11434`. The model the assistant uses is `spaceapp-asistente`.

## Embeddings model (search by meaning)

The RAG searches by words and, if the vectors and this model are present, also by meaning (`bge-m3`: multilingual, 1,024 dimensions, 1.16 GB). Without it the search keeps working by words only.

```bash
docker exec spaceapp-ollama ollama pull bge-m3          # 1.16 GB, once, with internet
.venv/bin/python -m spaceapp.modules.knowledge.ingest.embed   # computes the vectors; it is incremental
```

Each query costs about 200 ms of embedding. Ollama is asked for a `keep_alive` of 30 minutes so the model is not reloaded (≈ 4 s) on every question. The Ollama address of the development server is changed with `SPACEAPP_OLLAMA_URL`.

## Measurements on this machine (16 logical threads, Docker Desktop with 4 GB, other containers running)

| Test | Result |
|---|---|
| First answer with the model not loaded | 190 s (load 9.8 s; the rest, generating 450 tokens) |
| Generation with the default threads (16) | **2.6 to 2.7 tok/s** |
| Generation with 4 threads | **5.8 to 6.5 tok/s** (with 2: 5.2; with 6: 5.6; with 8: 4.5) |
| `spaceapp-asistente` (4 threads, 150 tokens max.) | 5.7 tok/s; 109 tokens in 28 s |
| Container memory with the model loaded | 2.5 GB of the 4 GB Docker Desktop gives |
| Tool calling (`/api/chat` with `tools`) | works: it calls `search_passages` with a reasonable query, also on an out-of-scope question |

**What it means:** with 16 threads the model competes with the other containers and is slower than with 4. A 150-token answer takes about 25 to 30 s; a 450-token one, over a minute. That is why the assistant cannot promise the plan's 8 s: the template with the passages comes out instantly and the model's wording arrives later.

**Observed quality (one sample, not an evaluation):** with a passage about CO₂ and headache in the prompt, the unbounded model answered long and generic ("I cannot provide a specific medical answer...") instead of relying on the passage. The length must be limited and the instructions fixed in n8n, and evaluated with the questions of `data/knowledge/eval_questions*.json` (phase 6).

## Smaller model: qwen2.5:1.5b (tried and discarded as an agent)

Downloaded with the user's permission (0.99 GB). Variant `spaceapp-asistente-rapido` in `docker/ollama/Modelfile.qwen1.5b`.

| | llama3.2:3b | qwen2.5:1.5b |
|---|---|---|
| Speed (4 threads) | 6.9 tok/s | **14 to 16 tok/s** (twice) |
| Does it call the search tool? | yes | **no, in 0 of 20 questions** |
| Main evaluation through n8n | 9 of 16 with the model's wording, 64 s on average | 9 of 16 **but 16 of 16 through the fallback template**, 4.3 s on average |

The small model ignores the order to use `search_passages` and answers from memory ("The capital of France is Paris"). The backend detects it (no passages were retrieved), discards that text and answers with the template: **the safety worked, but the model is no use as an agent**. The 4.3 s on average are the template's, not a wording's. The default flow stays with llama3.2:3b.

## Limits

- Measurements with variable load (load average of 7 to 12 during the tests): on another machine or without the other containers they will differ.
- No GPU. AVX2 yes, AVX-512 no.
- The image is heavy; for the offline delivery (F9) image and volume are prepared beforehand with a connection.
