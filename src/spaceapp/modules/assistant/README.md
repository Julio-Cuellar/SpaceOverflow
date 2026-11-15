# assistant · text assistant

Answers crew questions **only with retrieved passages** and cites them. It **never decides or changes an alert**: it can only name the active ones.

## Answer policy (`application/ask.py`)

1. Looks up passages with `KnowledgeQuery`. With no relevant passage it answers "I don't have that information in the loaded sources." and **does not call the model**.
2. With passages, it composes the answer with an `LlmGateway` within an **8 s time limit**. If the model takes longer, fails or does not exist, it answers with the passages as plain text.
3. The **citations are set by the use case**, not by the model.
4. Publishes `assistant.answer_ready` (`AnswerReady`: `utterance_id`, `text`, `citations[]`). An empty question is neither stored nor published.

The assistant works in English only: questions, passages and answers.

## `LlmGateway` adapters

- `NullLlmGateway`: no model; the use case uses the template. It guarantees that everything works without Ollama or a network.
- `OllamaGateway`: local Ollama with streaming (NDJSON). The model is given at creation; none has been chosen yet.

## Tests

```bash
.venv/bin/python -m pytest tests/assistant -q
```

## Current limits

- Text only. Voice (F14) and confirmation of the transcribed text are not done.
- Conversations live in memory; the `assistant` schema in PostgreSQL and its migration are missing.
- The GraphQL resolvers (`askAssistant`, `conversation`) are missing; they are registered in the schema that Dev A composes.
- The source of active alerts is a read-only port; today there is no real adapter (`ActiveAlertsQuery` of Monitoring).
