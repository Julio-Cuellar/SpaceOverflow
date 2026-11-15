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

El comando indexa los PDFs que haya en `data/knowledge/pdfs/` según `data/knowledge/manifest.json`. **No descarga nada**: los PDFs se ponen a mano (el manifiesto da la fuente y la licencia).

```bash
.venv/bin/python -m spaceapp.modules.knowledge.ingest --rebuild   # extrae, fragmenta y guarda en data/knowledge/index/chunks.jsonl
.venv/bin/python -m spaceapp.modules.knowledge.evaluate           # conjunto principal
.venv/bin/python -m spaceapp.modules.knowledge.evaluate --questions data/knowledge/eval_questions_validation.json
.venv/bin/python -m spaceapp.modules.knowledge.evaluate --questions data/knowledge/eval_questions_en.json
```

- Idempotente: reejecutarla no duplica. Usa `--rebuild` tras cambiar el fragmentado, o quedarán fragmentos viejos.
- Un PDF que falta, roto o sin texto se avisa y no detiene a los demás.
- Se fragmenta por referencia de requisito (`[V2 6004]`); una referencia citada a mitad de frase o dentro de un paréntesis abierto no parte el pasaje.
- Búsqueda BM25 con raíces de palabra y umbral (`MIN_SCORE`, `MIN_MATCHED_TERMS`); sin pasaje relevante devuelve lista vacía. Pregunta en español → `data/knowledge/glossary_es_en.json` (40 entradas, pendiente de revisión del equipo).
- **Los PDFs y el índice no se versionan:** la licencia de redistribución no está confirmada.

## Evaluación (métrica estricta, k=3)

Un acierto exige que el texto esperado aparezca en el extracto de los 3 primeros pasajes. Mínimo del plan: 80 %.

| Conjunto | Aciertos | Fuera de alcance respondidas |
|---|---|---|
| Principal (ES) | 9 de 16 (56 %) | 0 de 6 |
| Validación (ES, no se afinó con él) | 1 de 9 (11 %) | 0 de 6 |
| Diagnóstico (EN) | 13 de 25 (52 %) | 0 de 6 |

**No se alcanza el 80 %.** Nunca se responde fuera de alcance, pero la búsqueda léxica falla con paráfrasis y con cifras de tablas.

## Límites actuales

- Sin base de datos ni outbox: la idempotencia y el guardado son en memoria hasta el hito I1 (dev A).
- El asistente aún usa los pasajes de demostración: falta cablear la fuente RAG por perfil en `main.py` (dev A).
- La solución de fondo para la recuperación es un modelo de embeddings multilingüe (decisión pendiente; exige permiso para descargarlo).
- Los Technical Brief salen como `TB` aunque el catálogo de demostración marca TB-003 como `VERIFICADO`: decisión de equipo.
- Muchas cifras quedan sin `requirement_ref` propio: la cita lleva documento y página, no siempre número de requisito.
- No se extraen las tablas que vienen como imagen.
- `source_kind` (DEMO) no viaja en el evento: añadirlo exige pedírselo antes a Dev A.
