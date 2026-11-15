# knowledge · citable knowledge

Turns each alert into a **template recommendation with a citation**, without depending on any model, and searches for citable passages for the assistant.

## Contracts (`contracts.py`)

- Consumes `monitoring.alert_raised` (`AlertRaised`).
- Publishes `knowledge.recommendation_ready` (`RecommendationReady`): `alert_id`, `recommendation_id`, `action_keys[]`, `citations[]`.
- Read-only facades: `ActionCatalogQuery` (used by Missions) and `KnowledgeQuery` (used by the assistant).

## How it works

- Use case `HandleAlertRaised`: idempotent per `(consumer, event_id)`; an unknown rule raises `UnknownRuleError` **without** marking the event, so that the retry can process it.
- Source `DemoKnowledgeSource` reads `data/knowledge/demo_catalog.json` (25 rules, one for each Monitoring rule in `rules/catalog/monitoring.json`; 17 actions; 3 passages). `tests/knowledge/test_rule_coverage.py` cross-checks both catalogs: every rule Monitoring can raise has a recommendation, includes the action Monitoring names and no citation claims more evidence than the rule. Every recommendation says "demo data, not NASA data". The rule and action keys (`env-co2-pre`, `revisar_ventilacion_y_filtros`...) are identifiers shared with Monitoring and Missions: they stay as they are; only their texts are in English.
- Passage search: terms without accents or capitals, minimum relevance threshold; without a passage it returns an empty list.

## Tests

```bash
.venv/bin/python -m pytest tests/knowledge -q
```

## Ingesting the NASA PDFs (F12)

The command indexes the PDFs in `data/knowledge/pdfs/` according to `data/knowledge/manifest.json`. **It downloads nothing**: the PDFs are put there by hand (the manifest gives the source and the license).

```bash
.venv/bin/python -m spaceapp.modules.knowledge.ingest --rebuild   # extracts, fragments and stores in data/knowledge/index/chunks.jsonl
.venv/bin/python -m spaceapp.modules.knowledge.evaluate           # main set
.venv/bin/python -m spaceapp.modules.knowledge.evaluate --questions data/knowledge/eval_questions_validation.json
.venv/bin/python -m spaceapp.modules.knowledge.evaluate --questions data/knowledge/eval_questions_en.json
```

- Idempotent: running it again does not duplicate. Use `--rebuild` after changing the fragmenting, or old fragments will remain.
- A missing, broken or textless PDF is reported and does not stop the others.
- It fragments by requirement reference (`[V2 6004]`); a reference cited mid-sentence or inside an open parenthesis does not split the passage.
- BM25 search with word stems and a threshold (`MIN_SCORE`, `MIN_MATCHED_TERMS`); without a relevant passage it returns an empty list. A question in Spanish goes through `data/knowledge/glossary_es_en.json` (about 85 entries, pending team review); the assistant itself answers only in English.
- **Hybrid search (words + meaning):** `python -m spaceapp.modules.knowledge.ingest.embed` computes the vectors with `bge-m3` (local Ollama, 1,024 dimensions; it is incremental and stores `embeddings.json` and `.f32` next to the index). `build_knowledge_source` lets the words (BM25) propose the 50 best candidates and the cosine reorder them; those within 0.02 of the best cosine count as a tie and keep the word order. Meaning alone does not decide that there is an answer: if the words find nothing, or no candidate is similar enough (cosine ≥ 0.5), nothing is cited. Without vectors, with another model or without Ollama, it searches by words only. It costs ≈ 0.1 to 0.2 s per new question (embedding included).
- **The PDFs and the index are not versioned:** the redistribution license is not confirmed.

## Evaluation (strict metric, k=3)

A hit requires the expected text to appear in the excerpt of the first 3 passages. Plan minimum: 80%. `evaluate --mode lexical|hybrid --diagnose` prints recall@1/3/5/10, MRR and the rank at which each miss ended up. The reserved set (`eval_questions_reserved.json`, 30 useful questions and 8 out of scope) is frozen: it is not used to tune anything.

| Set | Lexical @3 | Hybrid @1 | Hybrid @3 | Hybrid @10 | Out of scope answered (hybrid) |
|---|---|---|---|---|---|
| Main ES (16) | 56% | 44% | 81% | 81% | 0 of 2 |
| Validation ES (9) | 67% | 56% | 67% | 78% | 0 of 1 |
| Diagnosis EN (25) | 56% | 48% | 68% | 80% | 0 of 3 |
| Reserved (30) | 60% | 57% | **80%** | 87% | 0 of 8 |

80% at @3 is reached in the main and reserved sets, **not** in validation (67%, only 9 questions) nor in English (68%). The ceiling is recall@10: passages the words do not find in their first 50 are not retrieved. The reserved set has been measured several times (see logbook E24): its figure is no longer from a single measurement.

## Current limits

- No database or outbox: idempotency and storage are in memory until milestone I1 (dev A).
- The assistant still uses the demo passages: the RAG source per profile must be wired in `main.py` (dev A).
- The vectors are not versioned (like the index): each machine computes them with `ingest.embed` (≈ 25 min on CPU for 1,588 fragments).
- The Technical Briefs come out as `TB` although the demo catalog marks TB-003 as `VERIFICADO`: team decision.
- The evidence states (`VERIFICADO`, `NO_VERIFICADO`, `TB`, `DEMO`) are shared vocabulary with Monitoring and the web: they keep their Spanish names.
- Many figures are left without their own `requirement_ref`: the citation carries document and page, not always a requirement number.
- Tables that come as an image are not extracted.
- `source_kind` (DEMO) does not travel in the event: adding it requires asking Dev A first.
