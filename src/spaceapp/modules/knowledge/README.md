# knowledge · conocimiento citable

Convierte cada alerta en una **recomendación de plantilla con cita**, sin depender de ningún modelo, y busca pasajes citables para el asistente.

## Contratos (`contracts.py`)

- Consume `monitoring.alert_raised` (`AlertRaised`).
- Publica `knowledge.recommendation_ready` (`RecommendationReady`): `alert_id`, `recommendation_id`, `action_keys[]`, `citations[]`.
- Fachadas de solo lectura: `ActionCatalogQuery` (usada por Misiones) y `KnowledgeQuery` (usada por el asistente).

## Cómo funciona

- Caso de uso `HandleAlertRaised`: idempotente por `(consumidor, event_id)`; una regla desconocida lanza `UnknownRuleError` **sin** marcar el evento, para que el reintento pueda procesarlo.
- Fuente `DemoKnowledgeSource` lee `data/knowledge/demo_catalog.json` (8 reglas, 15 acciones, 3 pasajes). Toda recomendación dice «dato de demostración, no de NASA».
- Búsqueda de pasajes: términos sin acentos ni mayúsculas, umbral mínimo de relevancia; sin pasaje devuelve lista vacía.

## Pruebas

```bash
.venv/bin/python -m pytest tests/knowledge -q
```

## Límites actuales

- Sin base de datos ni outbox: la idempotencia y el guardado son en memoria hasta el hito I1 (dev A).
- El RAG real sobre PDFs de NASA (F12) no está hecho; los pasajes son de demostración con su estado de evidencia.
- `source_kind` (DEMO) no viaja en el evento: añadirlo exige pedírselo antes a Dev A.
