# knowledge · citable knowledge

Turns each alert into a **template recommendation with a citation**, without depending on any model, and looks up citable passages for the assistant. The whole module works in English only.

## Contracts (`contracts.py`)

- Consumes `monitoring.alert_raised` (`AlertRaised`).
- Publishes `knowledge.recommendation_ready` (`RecommendationReady`): `alert_id`, `recommendation_id`, `action_keys[]`, `citations[]`.
- Read-only facades: `ActionCatalogQuery` (used by Missions) and `KnowledgeQuery` (used by the assistant).

## How it works

- Use case `HandleAlertRaised`: idempotent by `(consumer, event_id)`; an unknown rule raises `UnknownRuleError` **without** marking the event, so that the retry can process it.
- Source `DemoKnowledgeSource` reads `data/knowledge/demo_catalog.json` (25 rules, one for each Monitoring rule in `rules/catalog/monitoring.json`; 17 actions; 3 passages). `tests/knowledge/test_rule_coverage.py` cross-checks both catalogs: every rule that Monitoring can raise has a recommendation, includes the action that Monitoring names, and no citation claims more evidence than the rule. Every recommendation says "This recommendation uses demonstration data, not NASA data."
- Passage search: lowercase terms, minimum relevance threshold; with no passage it returns an empty list.

## Tests

```bash
.venv/bin/python -m pytest tests/knowledge -q
```

## Ingesting NASA PDFs (F12)

The command indexes the PDFs found in `data/knowledge/pdfs/` according to `data/knowledge/manifest.json`. It **downloads nothing**: the PDFs are placed by hand (the manifest gives the source and the license).

```bash
.venv/bin/python -m spaceapp.modules.knowledge.ingest --rebuild   # extracts, chunks and saves to data/knowledge/index/chunks.jsonl
.venv/bin/python -m spaceapp.modules.knowledge.evaluate           # main set
.venv/bin/python -m spaceapp.modules.knowledge.evaluate --questions data/knowledge/eval_questions_validation.json
```

- Idempotent: running it again does not duplicate. Use `--rebuild` after changing the chunking, or old chunks will remain. Rebuild as well after this translation: the document codes in the manifest are now in English (`OCHMO-TB-003 Habitable Atmosphere`, `OCHMO-TB-044 Medical Operations`, `Medical Kit Checklist`), so an index built earlier carries the old Spanish codes.
- A missing, broken or textless PDF is reported and does not stop the others.
- Chunking is by requirement reference (`[V2 6004]`); a reference cited mid-sentence or inside an open parenthesis does not split the passage.
- BM25 search with word stems and a threshold (`MIN_SCORE`, `MIN_MATCHED_TERMS`) over English questions and English documents, with an English stop-word list; with no relevant passage it returns an empty list. There is no translation layer: the Spanish-English glossary (`glossary_es_en.json`) was removed.
- **The PDFs and the index are not versioned:** the redistribution license is not confirmed.

## Evaluation (strict metric, k=3)

A hit requires the expected text to appear in the excerpt of the top 3 passages. Minimum in the plan: 80 %.

| Set | File | Cases |
|---|---|---|
| Main | `data/knowledge/eval_questions.json` | 16 in scope, 2 out of scope |
| Validation (not used for tuning) | `data/knowledge/eval_questions_validation.json` | 9 in scope, 1 out of scope |

The former Spanish sets and the English diagnostic set were merged: the main and validation sets are now the English questions, with the same expectations as before. The results below were measured **before** the English-only change, so they must be re-measured with the real PDFs indexed (they are not in the repository):

- English questions of both sets together (the former diagnostic set): 13 of 25 hits (52 %), 0 of 3 out-of-scope answered.
- The Spanish figures (main 9 of 16, validation 1 of 9) no longer apply.

**The 80 % has not been reached.** An out-of-scope question is never answered, but lexical search fails on paraphrases and on figures in tables.

## Current limits

- No database or outbox: idempotency and storage are in memory until milestone I1 (dev A).
- The assistant still uses the demonstration passages: wiring the RAG source per profile in `main.py` (dev A) is missing.
- The underlying fix for retrieval is an embeddings model (pending decision; it requires permission to download it).
- The Technical Briefs come out as `TB` although the demo catalog marks TB-003 as `VERIFIED`: team decision.
- Many figures have no `requirement_ref` of their own: the citation carries document and page, not always a requirement number.
- Tables that come as images are not extracted.
- `source_kind` (DEMO) does not travel in the event: adding it requires asking Dev A first.
