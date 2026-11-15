# n8n · orquestador del asistente

El asistente responde con un **agente de n8n**: modelo Ollama local, memoria por conversación y dos herramientas que vuelven a este backend (el RAG y las alertas activas). Los archivos de aquí se importan con la CLI de n8n; el workflow es dato versionado, no algo que viva solo en la interfaz.

| Archivo | Qué es |
|---|---|
| `workflows/space-apps-asistente.json` | Webhook → Config → Agente (Ollama + memoria + herramientas) → Responder |
| `credentials/ollama.json` | Credencial `ollamaApi` con la URL de Ollama (sin secretos) |

## Cómo funciona

1. El backend llama a `POST /webhook/space-apps-assistant` con `{turn_id, conversation_id, question, alerts}`.
2. El nodo **Config** guarda `backend_url` (por defecto `http://host.docker.internal:8000`) y los datos del turno. **Es el único sitio donde se cambia la dirección del backend.**
3. El agente usa `search_passages` (`POST {backend}/api/v1/assistant/tools/{turn_id}/search_passages`) y, si hace falta, `active_alerts` (solo lectura). La herramienta anota lo que devuelve: **de ahí salen las citas**, no de lo que el modelo diga.
4. El workflow responde `{"text": ...}`. Si falla o tarda, el backend responde con los pasajes en texto plano.

## Importar y activar

```bash
docker cp n8n/credentials/ollama.json n8n:/tmp/cred.json && docker exec n8n n8n import:credentials --input=/tmp/cred.json
docker cp n8n/workflows/space-apps-asistente.json n8n:/tmp/wf.json && docker exec n8n n8n import:workflow --input=/tmp/wf.json
docker exec n8n n8n publish:workflow --id=spaceAppsAsistente1
docker restart n8n                                  # el webhook solo se registra al arrancar
```

El workflow espera un modelo `spaceapp-asistente` en Ollama (ver `docker/ollama/README.md`). Probado también en un n8n recién creado (2.44.5): importa sin errores.

## Probarlo

```bash
python -m spaceapp.devtools.assistant_server        # backend de desarrollo en el puerto 8000
curl -X POST localhost:8000/dev/ask -H 'Content-Type: application/json' -d '{"text":"¿Por qué me duele la cabeza?"}'
```

## Privacidad y seguridad

- El workflow **no guarda ejecuciones** (`saveDataSuccessExecution` y `saveDataErrorExecution` en `none`): lo que pregunta la tripulación no queda en la base de n8n. Para depurar, actívalo a mano y vuelve a quitarlo.
- Las herramientas solo funcionan durante un turno abierto: sin un `turn_id` vivo devuelven 404.
- **El webhook no tiene autenticación.** Cualquiera que llegue al puerto de n8n puede lanzar una consulta al modelo (gasta CPU, no da acceso a nada más). En la entrega, publicar solo en `127.0.0.1` o añadir autenticación de cabecera.
- Si n8n se comparte con otros proyectos (aquí tiene otros 7 workflows), no arrancar su túnel de ngrok mientras el webhook esté activo.
