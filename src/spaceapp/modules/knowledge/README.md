# knowledge · conocimiento citable

Convierte cada alerta en una **recomendación de plantilla con cita**, sin depender de ningún modelo, y busca pasajes citables para el asistente.

## Contratos (`contracts.py`)

- Consume `monitoring.alert_raised` (`AlertRaised`).
- Publica `knowledge.recommendation_ready` (`RecommendationReady`): `alert_id`, `recommendation_id`, `action_keys[]`, `citations[]`.
- Fachadas de solo lectura: `ActionCatalogQuery` (usada por Misiones) y `KnowledgeQuery` (usada por el asistente).

## Cómo funciona

- Caso de uso `HandleAlertRaised`: idempotente por `(consumidor, event_id)`; una regla desconocida lanza `UnknownRuleError` **sin** marcar el evento, para que el reintento pueda procesarlo.
- Fuente `DemoKnowledgeSource` lee `data/knowledge/demo_catalog.json` (25 reglas, una por cada regla de Monitoreo de `rules/catalog/monitoring.json`; 17 acciones; 3 pasajes). `tests/knowledge/test_rule_coverage.py` cruza ambos catálogos: toda regla que Monitoreo puede levantar tiene recomendación, incluye la acción que Monitoreo nombra y ninguna cita dice más evidencia que la regla. Toda recomendación dice «dato de demostración, no de NASA».
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
- Búsqueda BM25 con raíces de palabra y umbral (`MIN_SCORE`, `MIN_MATCHED_TERMS`); sin pasaje relevante devuelve lista vacía. Pregunta en español → `data/knowledge/glossary_es_en.json` (unas 85 entradas, pendiente de revisión del equipo).
- **Búsqueda híbrida (palabras + significado):** `python -m spaceapp.modules.knowledge.ingest.embed` calcula los vectores con `bge-m3` (Ollama local, 1 024 dimensiones; es incremental y guarda `embeddings.json` y `.f32` junto al índice). `build_knowledge_source` fusiona BM25 y coseno con RRF. Sin vectores, con otro modelo o sin Ollama, busca solo por palabras. El significado no decide solo que hay respuesta: si las palabras no encuentran nada, no se cita nada (`require_word_match`). Cuesta ≈ 0,4 a 1 s por pregunta nueva (embedding incluido) y ≈ 0,2 s si ya se vio.
- **Los PDFs y el índice no se versionan:** la licencia de redistribución no está confirmada.

## Evaluación (métrica estricta, k=3)

Un acierto exige que el texto esperado aparezca en el extracto de los 3 primeros pasajes. Mínimo del plan: 80 %. `evaluate --mode lexical|hybrid --diagnose` imprime recall@1/3/5/10, MRR y en qué puesto quedó cada fallo. El conjunto reservado (`eval_questions_reserved.json`, 30 preguntas útiles y 8 fuera de alcance) está congelado: no se usa para ajustar nada.

| Conjunto | Léxico @3 | Híbrido @3 | Híbrido @10 | Fuera de alcance respondidas (híbrido) |
|---|---|---|---|---|
| Principal (ES, 16) | 56 % | 62 % | 88 % | 0 de 2 |
| Validación (ES, 9) | 67 % | 78 % | 89 % | 0 de 1 |
| Diagnóstico (EN, 25) | 56 % | 52 % | 84 % | 0 de 3 |
| Reservado (30) | 60 % | 70 % | 87 % | 1 de 8 (migraña en inglés; el léxico también la responde) |

**Todavía no se alcanza el 80 % en @3**, aunque la respuesta correcta suele estar en los 10 primeros puestos: lo que falta es ordenar mejor (un reordenador o más contexto en cada fragmento).

## Límites actuales

- Sin base de datos ni outbox: la idempotencia y el guardado son en memoria hasta el hito I1 (dev A).
- El asistente aún usa los pasajes de demostración: falta cablear la fuente RAG por perfil en `main.py` (dev A).
- Los vectores no se versionan (como el índice): cada máquina los calcula con `ingest.embed` (≈ 25 min en CPU para 1 588 fragmentos).
- Los Technical Brief salen como `TB` aunque el catálogo de demostración marca TB-003 como `VERIFICADO`: decisión de equipo.
- Muchas cifras quedan sin `requirement_ref` propio: la cita lleva documento y página, no siempre número de requisito.
- No se extraen las tablas que vienen como imagen.
- `source_kind` (DEMO) no viaja en el evento: añadirlo exige pedírselo antes a Dev A.
