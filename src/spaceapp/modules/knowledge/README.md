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

## Ingesta de PDFs de NASA (F12)

El comando indexa los PDFs que haya en `data/knowledge/pdfs/` según `data/knowledge/manifest.json`. **No descarga nada**: los PDFs se ponen a mano.

```bash
.venv/bin/python -m spaceapp.modules.knowledge.ingest      # extrae, fragmenta y guarda en data/knowledge/index/chunks.jsonl
.venv/bin/python -m spaceapp.modules.knowledge.evaluate    # mide el acierto y que nada fuera de alcance reciba respuesta
```

- Es idempotente: reejecutarla no duplica fragmentos. Un PDF que falta, roto o sin texto se avisa y no detiene a los demás.
- La búsqueda traduce la pregunta con `data/knowledge/glossary_es_en.json`, porque los documentos están en inglés.
- **Los PDFs y el índice no se versionan:** la licencia de redistribución no está confirmada (ver `manifest.json`).

## Límites actuales

- Sin base de datos ni outbox: la idempotencia y el guardado son en memoria hasta el hito I1 (dev A).
- La ingesta y la evaluación **no se han ejecutado con los PDFs reales**; el pipeline está probado con PDFs sintéticos. Los pasajes del asistente siguen siendo los de demostración hasta entonces.
- El glosario es una solución provisoria; la de fondo es un modelo de embeddings multilingüe (decisión pendiente).
- No se extraen las tablas que vienen como imagen.
- `source_kind` (DEMO) no viaja en el evento: añadirlo exige pedírselo antes a Dev A.
