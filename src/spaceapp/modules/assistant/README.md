# assistant · asistente de texto

Responde preguntas de la tripulación **solo con pasajes recuperados** y los cita. **Nunca decide ni cambia una alerta**: solo puede nombrar las activas.

## Política de respuesta (`application/ask.py`)

1. Busca pasajes con `KnowledgeQuery`. Sin pasaje relevante responde «No tengo esa información en las fuentes cargadas.» y **no llama al modelo**.
2. Con pasajes, redacta con un `LlmGateway` dentro de un **tiempo límite de 8 s**. Si el modelo tarda más, falla o no existe, responde con los pasajes en texto plano.
3. Las **citas las pone el caso de uso**, no el modelo.
4. Publica `assistant.answer_ready` (`AnswerReady`: `utterance_id`, `text`, `citations[]`). Una pregunta vacía no se guarda ni se publica.

## Adaptadores de `LlmGateway`

- `NullLlmGateway`: sin modelo; el caso de uso usa la plantilla. Es el que garantiza que todo funcione sin Ollama ni red.
- `OllamaGateway`: Ollama local en streaming (NDJSON). El modelo se indica al crearlo; no hay uno elegido todavía.

## Pruebas

```bash
.venv/bin/python -m pytest tests/assistant -q
```

## Límites actuales

- Solo texto. La voz (F14) y la confirmación de lo transcrito no están hechas.
- Conversaciones en memoria; falta el esquema `assistant` en PostgreSQL y su migración.
- Faltan los resolvers GraphQL (`askAssistant`, `conversation`), que se registran en el esquema que compone Dev A.
- La fuente de alertas activas es un puerto de solo lectura; hoy no hay adaptador real (`ActiveAlertsQuery` de Monitoreo).
