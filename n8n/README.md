# n8n · assistant orchestrator

The assistant answers with an **n8n agent**: a local Ollama model, memory per conversation and two tools that call back into this backend (the RAG and the active alerts). The files here are imported with the n8n CLI; the workflow is versioned data, not something that lives only in the interface.

| File | What it is |
|---|---|
| `workflows/space-apps-asistente.json` | Webhook → Config → Agent (Ollama + memory + tools) → Respond |
| `credentials/ollama.json` | `ollamaApi` credential with the Ollama URL (no secrets) |

## How it works

1. The backend calls `POST /webhook/space-apps-assistant` with `{turn_id, conversation_id, question, alerts}`.
2. The **Config** node stores `backend_url` (default `http://host.docker.internal:8000`) and the turn data. **It is the only place where the backend address is changed.**
3. The agent uses `search_passages` (`POST {backend}/api/v1/assistant/tools/{turn_id}/search_passages`) and, if needed, `active_alerts` (read-only). The tool records what it returns: **the citations come from there**, not from what the model says.
4. The workflow answers `{"text": ...}`. If it fails or is slow, the backend answers with the passages as plain text.

## Import and activate

```bash
docker cp n8n/credentials/ollama.json n8n:/tmp/cred.json && docker exec n8n n8n import:credentials --input=/tmp/cred.json
docker cp n8n/workflows/space-apps-asistente.json n8n:/tmp/wf.json && docker exec n8n n8n import:workflow --input=/tmp/wf.json
docker exec n8n n8n publish:workflow --id=spaceAppsAsistente1
docker restart n8n                                  # the webhook is only registered at startup
```

The workflow expects a `spaceapp-asistente` model in Ollama (see `docker/ollama/README.md`). Also tested on a freshly created n8n (2.44.5): it imports without errors.

## Try it

```bash
python -m spaceapp.devtools.assistant_server        # development backend on port 8000
curl -X POST localhost:8000/dev/ask -H 'Content-Type: application/json' -d '{"text":"Why do I have a headache?"}'
```

## Privacy and security

- The workflow **does not save executions** (`saveDataSuccessExecution` and `saveDataErrorExecution` set to `none`): what the crew asks does not stay in n8n's database. To debug, turn it on by hand and turn it off again.
- The tools only work during an open turn: without a live `turn_id` they return 404.
- **The webhook has no authentication.** Anyone who reaches the n8n port can send a query to the model (it uses CPU, it gives access to nothing else). For the delivery, publish only on `127.0.0.1` or add header authentication.
- If n8n is shared with other projects (here it has 7 other workflows), do not start its ngrok tunnel while the webhook is active.
