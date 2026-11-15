# Plan and artifact generator

Generates `docs/architecture-plan.md` and the interactive plan page from a single source, so that the tables,
the diagrams and the artifact do not contradict each other.

| File | What it is |
| --- | --- |
| `data.py` | Data: modules, events, tables, sequences, phases, split, incident catalog |
| `template.md` | Document text, with `{{NAME}}` placeholders that the generator fills in |
| `page.html` | Interactive artifact (HTML, CSS and JS). Receives the data in `const D = …` |
| `build.py` | Generates the document and the page |

## Usage

```bash
# regenerates docs/architecture-plan.md and tools/docgen/out/plan.html
uv run python tools/docgen/build.py --artifact-url https://claude.ai/artifact/LMrTxLRghTr9h3v2Q79am8
```

Options: `--template`, `--page`, `--out-md` and `--out-html`.

## Rules

- **Do not edit `docs/architecture-plan.md` by hand.** Change `data.py` or `template.md` and regenerate.
  The test `tests/unit/test_docgen.py` fails if the document does not match what the source generates.
- A template with an unknown placeholder makes the generation fail and names the placeholder.
- `page.html` is the source of the artifact. To publish a new version, regenerate and publish
  `tools/docgen/out/plan.html` over the same address.
- The `out/` folder is in `.gitignore`.

## Origin

These files used to live in a temporary folder of the working session. Since entry B-011 of
`logbook-dev-a.md` the source is here.
