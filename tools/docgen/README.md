# Generador del plan y del artefacto

Genera `docs/plan-arquitectura.md` y la página interactiva del plan desde una sola fuente, para que las tablas,
los diagramas y el artefacto no se contradigan.

| Archivo | Qué es |
| --- | --- |
| `data.py` | Datos: módulos, eventos, tablas, secuencias, fases, reparto, catálogo de incidencias |
| `template.md` | Texto del documento, con marcadores `{{NOMBRE}}` que el generador rellena |
| `page.html` | Artefacto interactivo (HTML, CSS y JS). Recibe los datos en `const D = …` |
| `build.py` | Genera el documento y la página |

## Uso

```bash
# regenera docs/plan-arquitectura.md y tools/docgen/out/plan.html
uv run python tools/docgen/build.py --artifact-url https://claude.ai/artifact/LMrTxLRghTr9h3v2Q79am8
```

Opciones: `--template`, `--page`, `--out-md` y `--out-html`.

## Reglas

- **No edite `docs/plan-arquitectura.md` a mano.** Cambie `data.py` o `template.md` y regenere.
  La prueba `tests/unit/test_docgen.py` falla si el documento no coincide con lo que genera la fuente.
- Una plantilla con un marcador desconocido hace fallar la generación y nombra el marcador.
- `page.html` es la fuente del artefacto. Para publicar una versión nueva, regenere y publique
  `tools/docgen/out/plan.html` sobre la misma dirección.
- La carpeta `out/` está en `.gitignore`.

## Origen

Estos archivos vivían en una carpeta temporal de la sesión de trabajo. Desde la entrada B-011 de
`docs/bitacora.md` la fuente está aquí.
