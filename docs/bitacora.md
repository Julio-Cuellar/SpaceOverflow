# Bitácora del proyecto

> NASA Space Apps 2026 · monitor de salud para astronautas
> Registro cronológico de lo que se hace y de cada cambio que se produce, incluidos los que se hacen **fuera del repositorio** (instalaciones, servicios) y los errores corregidos.
> Última actualización: 15 de noviembre de 2026, 05:30.

## Cómo se mantiene esta bitácora

- Cada bloque de trabajo agrega **una entrada nueva al final** de la sección 3, antes de cerrar.
- Una entrada tiene: qué se hizo, archivos creados o cambiados, cómo se verificó y con qué resultado, decisiones y pendientes.
- Los errores se registran tal como ocurrieron, con su corrección. Se escriben en la sección 6 y se referencian desde la entrada.
- Lo que se hace en el equipo del usuario (instalar, arrancar servicios, descargar) se anota en la sección 5. Nunca queda sin registrar.
- Las horas de los hitos son de trabajo por persona, no de reloj. Las horas de reloj de esta bitácora salen de las fechas de modificación de los archivos.

### Plantilla de entrada

```markdown
### B-0XX · Título corto
- **Qué:** …
- **Archivos:** …
- **Verificación:** comando → resultado
- **Decisiones:** …
- **Pendiente:** …
```

---

## 1. Estado actual

| Área | Estado |
| --- | --- |
| Plan de arquitectura | Redactado y **pendiente de confirmación** por el usuario |
| Reparto en dos desarrolladores | Redactado (sección 16 del plan) y detallado para Dev B |
| Plan detallado de Dev A | `docs/tareas-dev-a.md` (F0 y F1 marcadas como hechas) |
| Generador del plan y del artefacto | En el repositorio (`tools/docgen/`), con prueba que verifica que reproduce el documento |
| Código | **Bloques 1 y 2 de Dev A terminados** (F0 a F3). **F4, F5, F10 y F11 terminadas** del lado del backend (pendientes menores: DataLoaders, límite de costo, consentimiento y Tripulación). F9 queda para cuando la interfaz esté lista (decisión del usuario). El trabajo de Dev B (F0, F6 a F8, F12, F13) ya está integrado desde `testing` |
| Pruebas | **707 pasan y 19 se omiten** (las omitidas son de Dev B), 95,89 % de cobertura, ruff y mypy estricto sin errores, 4 contratos de arquitectura cumplidos |
| Artefacto interactivo | Versión 4 publicada: https://claude.ai/artifact/LMrTxLRghTr9h3v2Q79am8 |
| Repositorio git | El trabajo vive en `~/Documentos/SpaceOverflow`, rama `dev-A`. **Subida a GitHub** (B-021): fusiones B-015 y B-016, F5, 5.4 y F4. Falta el PR hacia `testing` |
| Siguiente bloque propuesto | Subir `dev-A` y que Dev B conecte tareas y panel de Tierra. F9 cuando la interfaz esté lista |

---

## 2. Decisiones

### 2.1 Tomadas por el usuario

| Decisión | Dónde quedó |
| --- | --- |
| Reto: monitoreo de salud para astronautas | Contexto del proyecto |
| Funcionamiento autónomo, sin enlace con Tierra | Contexto, plan sección 1 |
| Python con FastAPI, PostgreSQL, GraphQL y WebSockets | Plan sección 4 |
| Arquitectura hexagonal como monolito modular con bus de eventos y outbox | Plan sección 5 y 6 |
| Panel de la nave con plano, tickets de incidencia y gases por zona | Plan 13.7 |
| Tareas diarias de la tripulación: salud, nave e incidentes | Plan 13.8 |
| Catálogo de tipos de incidencia en el plan y el artefacto | Plan 13.9 |
| **Opción B:** el centro de control programa tareas con planes versionados, y la tripulación crea las suyas | Plan 13.11 |
| Dividir el plan entre dos desarrolladores, con **todo el RAG en uno solo** | Plan sección 16 |
| Ejecutar el plan de Dev A empezando por el Bloque 1 | Entrada B-008 |

### 2.2 Supuestos míos (el usuario no los ha confirmado)

| Supuesto | Por qué | Efecto si cambia |
| --- | --- | --- |
| Interfaz con React, Vite y TypeScript | No se indicó frontend. Se contestó que era lo más conveniente | Solo cambia `web/` |
| Variable `SPACEAPP_PROFILE` con `jurado` por defecto | Funciona sin internet ni Alexa | Un cambio en `config.py` |
| Autenticación por selección de perfil local | Sin cuentas externas | Afecta al panel de Tierra |
| n8n como adaptador opcional de Ollama | Ahorra una pieza en 48 h | Afecta a `LlmGateway` |
| Python 3.12 con `uv` en lugar del 3.14 del sistema | Evita ruedas binarias no disponibles | Ninguno si se mantiene 3.12 |
| Base de datos de desarrollo en el puerto 5433 | El 5432 lo usa otro proyecto del usuario | Variable `SPACEAPP_DB_PORT` |
| Ventana de 10 s para la regla de velocidad de presión (`env-dpdt`) | Una fuga real promedia unos 6 psi/min en 60 s y no llegaba a 13,5. La norma no fija la ventana | Un cambio en el catálogo JSON |
| Ventanas de las reglas escalables con `rule_window_scale` (1,0 por defecto) | Una ventana de 1 h hace inviable la demostración | Solo cambia la configuración |
| Relay y simulador apagados por defecto (`SPACEAPP_RELAY_ENABLED`, `SPACEAPP_SIMULATOR_AUTOSTART`) | Con el simulador apagado el sistema arranca igual. En F9 se activan para el perfil `jurado` | Cambia el valor por defecto |
| Categoría de consentimiento «tareas» activa por defecto | Tierra necesita ver el estado de sus tareas | Cambia el consentimiento por defecto |
| Catálogo de 61 tipos de incidencia como propuesta | No existe una lista oficial citable | Solo los `VERIFICADO` salen de la norma |

### 2.3 Pendientes de decidir

1. El RAG: ¿solo devuelve pasajes con cita o también redacta con Ollama?
2. ¿n8n sigue como orquestador o se llama a Ollama directo?
3. ¿Se sube F12 (RAG completo) a P0? Cabe en la holgura de Dev B antes de la entrega.
4. Modelo de embeddings local (hoy la búsqueda empieza por texto completo).
5. Autenticidad del plan de Tierra: solo hash o firma criptográfica.
6. Alcance del panel de Tierra: misma SPA con rol `ground` o despliegue aparte.
7. Escenario de la demo (tránsito a Marte, base lunar o ISS), idioma para el jurado y tamaño del equipo.
8. Usuarios reales para `CODEOWNERS`.

---

## 3. Registro cronológico

### B-001 · Carga del contexto
- **Qué:** se leyeron los dos documentos de `docs/` (el contexto consolidado y la exportación de Notion) y se resumió el estado del proyecto.
- **Archivos:** ninguno modificado.
- **Hallazgo:** en Notion varios documentos aparecen como «No abierto» aunque ya se leyeron. El contexto consolidado tiene el estado real.

### B-002 · Plan de arquitectura, primera versión
- **Qué:** plan de arquitectura hexagonal con monolito modular y bus de eventos con outbox. Incluye diagramas ER, de secuencia y de comunicación entre módulos, y la tabla de canales y eventos (REST, GraphQL y WebSocket).
- **Archivos:** `docs/plan-arquitectura.md` (nuevo). Artefacto **versión 1** (nuevo).
- **Método:** el documento y el artefacto se generan desde una misma fuente de datos (ver sección 7) para que no se contradigan.
- **Verificación:** el artefacto se abrió en el navegador integrado y no mostró errores de consola.

### B-003 · Artefacto versión 2
- **Qué (a petición del usuario):**
  - relaciones visibles en el diagrama ER, con líneas y cardinalidad,
  - colores por participante en los diagramas de secuencia,
  - cuerpo humano con 6 indicadores en el panel de cabina,
  - panel de la nave: plano de 10 zonas, tickets, gráficas de gases por zona y alertas por anomalía,
  - tareas diarias de salud, nave e incidentes.
- **Cambios de arquitectura:** módulo nuevo `facility` (nave e incidencias), 4 eventos nuevos y tablas `habitat`, `zone`, `incident` e `incident_update`.
- **Verificación:** prueba de un escenario de fuga de presión en el navegador (se pintó la zona y se abrió el ticket) y 40 líneas de relación en el ER sin valores inválidos.

### B-004 · Catálogo de incidencias y opción B (artefacto versión 3)
- **Qué:**
  - catálogo de 61 tipos de incidencia en 12 categorías, con formulario de reporte por categoría y tipo,
  - plan de tareas desde Tierra (opción B) con panel del centro de control, reglas de conflicto y tareas propias de la tripulación,
  - 4 eventos, 9 operaciones GraphQL, 1 ruta REST, 1 mensaje WebSocket y 5 tablas nuevas.
- **Cambio de nombre:** el módulo `uplink` pasó a `groundlink` (ver error E-2 en la sección 6).
- **Verificación:** flujo completo en el navegador (cortar enlace, publicar, restablecer, aplicar, tarea propia, bloqueo) y los tres casos de prueba del plan (corrupto, repetido, ítem inválido).

### B-005 · Reparto entre dos desarrolladores (artefacto versión 4)
- **Qué:** sección 16 del plan. Dev A lleva el núcleo y el tiempo real (31 h). Dev B lleva la interfaz, Conocimiento y todo el RAG (34 h, de las cuales 15 h son RAG). Incluye línea de tiempo, 8 hitos de integración, contratos cruzados y reglas para no bloquearse.
- **Corrección:** el corte P0 son **40 h** (21,5 h A y 18,5 h B), no 41 h como se dijo antes (error E-1).
- **Verificación:** el planificador calculó las colas de trabajo y los hitos. Se comprobó que las horas por fase suman el total.

### B-006 · Documento de tareas de Dev B
- **Qué:** documento con todas las tareas de Dev B por fase, con subtareas y estimaciones, criterios de aceptación, contratos, esquemas, pruebas, riesgos y checklist.
- **Archivos:** `docs/tareas-dev-b.md` (nuevo).
- **Verificación:** las horas de las subtareas de cada fase suman su total (34 h) y los contratos se contrastaron con los datos del plan.

### B-007 · Plan de ejecución de Dev A
- **Qué:** plan inline con los 4 bloques de trabajo, los archivos a crear y los riesgos. Se revisó el equipo antes de planificar.
- **Hallazgos del equipo:** sin repositorio ni código, Python 3.14.4 del sistema (el plan pide 3.12), sin `pip` ni `uv`, Docker con el daemon apagado, sin PostgreSQL ni Node.
- **Archivos:** ninguno (solo conversación).

### B-008 · Ejecución del Bloque 1 de Dev A: F0 y F1
- **Qué:** implementación con TDD (prueba primero, RED, código mínimo, GREEN, refactor).
- **Archivos nuevos (45 módulos de Python, 80 en `src/`, 17 en `tests/`):**

| Ruta | Contenido |
| --- | --- |
| `pyproject.toml`, `uv.lock`, `.python-version` | Proyecto con Python 3.12 y dependencias |
| `src/spaceapp/platform/` | `events.py`, `bus.py`, `profiles.py`, `config.py`, `vocab.py`, `db.py`, `migrate.py` |
| `src/spaceapp/platform/outbox/` | `publisher.py`, `uow.py`, `relay.py`, `stats.py` |
| `src/spaceapp/modules/<9 módulos>/` | `contracts.py`, `facade.py` y paquetes `domain`, `application`, `ports`, `adapters` |
| `src/spaceapp/event_registry.py` | Registro de los 22 eventos |
| `src/spaceapp/main.py` | Composition root con `/health` y `/ready` |
| `migrations/platform/` | Migración del outbox y el inbox |
| `tests/` | 122 pruebas: unitarias, de contrato, de arquitectura e integración |
| `docker/compose.yaml` | PostgreSQL con pgvector |
| `Makefile`, `scripts/check.sh` | Verificación completa |
| `CODEOWNERS`, `README.md`, `.gitignore` | Repositorio |

- **Verificación** (`scripts/check.sh`):

| Control | Resultado |
| --- | --- |
| ruff | Sin errores |
| mypy estricto | Sin errores en 80 archivos |
| import-linter | 4 contratos cumplidos, 0 rotos |
| pytest | 122 pasan |
| Cobertura | 98,99 % (mínimo exigido 80 %) |
| Prueba real | `docker compose up`, migración por línea de comandos, `/health` 200 y `/ready` 200 |

- **RED documentado:** 5 errores de colección en F0 y 3 en F1, todos por módulos inexistentes.
- **Hitos que habilita:** I0 (contratos listos para revisión de Dev B) e I1 (outbox real disponible).
- **Pendiente:** el Bloque 2 (F2 y F3).

### B-009 · Informe de evidencia TDD
- **Qué:** informe con los RED y GREEN reales, las incidencias durante el ciclo, una tabla de 24 garantías y los huecos de cobertura.
- **Archivos:** `docs/tdd/f0-f1.tdd.md` (nuevo).
- **Verificación:** los conteos por archivo se contrastaron con `pytest --collect-only`. Una primera versión tenía 4 cifras por archivo equivocadas y se corrigió (suman 122).

### B-010 · Esta bitácora
- **Qué:** registro completo de lo hecho en la sesión, con cambios fuera del repositorio, errores y pendientes.
- **Archivos:** `docs/bitacora.md` (nuevo).

### B-011 · Generador del plan dentro del repositorio
- **Qué:** se movió la fuente del plan y del artefacto (antes en una carpeta temporal de la sesión) a `tools/docgen/`. Se le dio una línea de comandos y una prueba que garantiza que reproduce el documento.
- **Archivos:**
  - nuevos: `tools/docgen/{data.py, build.py, template.md, page.html, README.md}` y `tests/unit/test_docgen.py`,
  - cambiados: `pyproject.toml` (ruff ignora `tools`) y `.gitignore` (ignora `tools/docgen/out/`).
- **Cambios en `build.py`:** deja de usar rutas fijas y recibe `--artifact-url`, `--template`, `--page`, `--out-md` y `--out-html`. Un marcador desconocido en la plantilla hace fallar la generación y lo nombra.
- **TDD:** primero 3 pruebas (RED: `can't open file 'tools/docgen/build.py'`). Después el generador (GREEN, 3 pasan). La tercera prueba de la primera versión era floja (solo comprobaba `stderr == ""`) y se reemplazó por una real (error E-11).
- **Verificación:** el generador del repositorio reproduce `docs/plan-arquitectura.md` **byte a byte** (`diff` sin diferencias) y genera la página sin marcadores sin resolver.
- **Decisión:** `docs/plan-arquitectura.md` no se edita a mano. Se cambia `data.py` o `template.md` y se regenera.
- **No se hizo:** no se volvió a publicar el artefacto, porque su contenido no cambió.

### B-012 · Documento de tareas de Dev A
- **Qué:** documento equivalente al de Dev B, con las 10 fases de A en detalle (F0 y F1 marcadas como hechas), contratos, flujo de una alerta por zona, mapa de eventos a mensajes WebSocket, vectores de prueba, riesgos, coordinación y decisiones pendientes.
- **Archivos:** `docs/tareas-dev-a.md` (nuevo). `tools/docgen/template.md` (enlace a los dos documentos de tareas en la sección 16.1) y `docs/plan-arquitectura.md` (regenerado con la herramienta).
- **Verificación:** las subtareas de cada fase suman su total (31 h). Una primera versión tenía F2 en 4,25 h (error E-12) y se corrigió. Los contratos de A se extrajeron de los datos del plan: 7 rutas REST, 31 operaciones GraphQL, 14 mensajes WebSocket y 19 eventos publicados.
- **Hallazgo:** el plan define el mensaje `alert.updated` pero no existe un evento de dominio que lo origine. Quedó como decisión pendiente del Dev A (sección 10 de su documento).
- **Verificación final:** `scripts/check.sh` en verde con 125 pruebas y 98,99 % de cobertura.

### B-013 · Ejecución del Bloque 2 de Dev A: F2 y F3
- **Qué:** monitoreo con catálogo de reglas, motor determinista y ciclo de vida de alertas (F2), y telemetría con simulador, ingesta idempotente y rollup (F3). TDD en todo el bloque.
- **Archivos nuevos (168 pruebas más):**

| Ruta | Contenido |
| --- | --- |
| `src/spaceapp/modules/monitoring/` | Dominio (`units`, `physics`, `series`, `trend`, `rules`, `engine`, `lifecycle`), catálogo JSON, repositorios SQL y en memoria, handler `EvaluateReadings`, `acknowledge_alert`, fachadas, endpoint del catálogo |
| `src/spaceapp/modules/telemetry/` | Dominio (`readings`, `simulator`, `layout`), ingesta, rollup, servicio del simulador, repositorio SQL, `SqlReadingQuery`, REST R1 y R4 |
| `src/spaceapp/platform/ids.py`, `migrations_env.py` | Identificadores estables y entorno de Alembic compartido |
| `rules/catalog/monitoring.json` | 25 reglas (20 de umbral y 5 de tendencia) con fuente y estado de evidencia |
| `data/telemetry/sim_layout.json` | Las 10 zonas simuladas |
| `migrations/monitoring/`, `migrations/telemetry/` | Migraciones propias (reglas y alertas; sensores, lecturas particionadas por día, rollup y escenarios) |
| `tests/unit/{monitoring,telemetry}/`, `tests/integration/{monitoring,telemetry}/` | Las pruebas nuevas |
| `docs/tdd/f2-f3.tdd.md` | Informe de evidencia |

- **Archivos cambiados:** `src/spaceapp/main.py` (arranque del relay y del simulador por configuración, routers), `src/spaceapp/platform/config.py` (ajustes nuevos), `tests/conftest.py` (migra y limpia los tres esquemas), `pyproject.toml` (reglas de ruff para SQL y pruebas), `tools/docgen/data.py` y `template.md` (modelo de datos), `docs/plan-arquitectura.md` (regenerado) y `docs/tareas-dev-a.md` (estado y diferencias).
- **Verificación** (`scripts/check.sh`): ruff sin errores, mypy estricto sin errores en 113 archivos, 4 contratos de arquitectura cumplidos, 293 pruebas, 97,53 % de cobertura.
- **Prueba en vivo con el reloj real:** 130 s normales → 1.930 lecturas y 0 alertas. Escenario de CO₂ en el laboratorio → tendencia (Atención), pre-alerta (Atención) y alerta verificada (Alerta, `VERIFICADO`), solo en esa zona, sin errores en el log y con el outbox vacío.
- **Decisiones:**
  - Cada regla tiene severidad fija. Subir de nivel es resolver la alerta leve y levantar la grave, así que **no hace falta `monitoring.alert_escalated`** (la decisión pendiente del plan queda resuelta).
  - Las ventanas de las reglas exigen que los datos cubran al menos la mitad de la ventana. El tiempo de demostración se acelera con `rule_window_scale`.
  - El detector de tendencia y la regla de velocidad de presión se ajustaron por lo que el simulador mostró (ver E-14 y E-15).
- **Diferencias con lo planeado:** el handler de `crew.baseline_updated` y `BaselineQuery` no se hicieron (aún no hay reglas relativas a la línea base). Detalle en `docs/tareas-dev-a.md`, sección 3.3.
- **Hallazgo del plan:** el hito I2 pide conectar los ticks por WebSocket, pero el gateway es F5. I2 se cumple solo en la parte del simulador.
- **Pendiente:** Bloque 3 (F4 y F5). Medir el rendimiento de Monitoreo con las ventanas reales de 1 h.


### B-014 · Trabajo de Dev A llevado al repositorio SpaceOverflow (rama dev-A)
- **Qué:** se clonó `https://github.com/Julio-Cuellar/SpaceOverflow` en `~/Documentos/SpaceOverflow` y se copió ahí el trabajo de Dev A (F0 a F3) sobre la rama `dev-A`, que ya existía en el remoto con solo el primer commit.
- **Cómo:** se copiaron los 192 archivos que respeta `.gitignore` (sin `.venv`, cachés ni `.git`). El `README.md` de la plantilla (`# SpaceOverflow`) se reemplazó por el del proyecto.
- **Estado del remoto al clonar:** `main` y `dev-A` solo tienen el primer commit; `dev-B` y `testing` ya tienen trabajo de Dev B (`pyproject.toml`, `.gitignore`, `src/spaceapp/__init__.py`, `.github/CODEOWNERS`, CI, etc.).
- **Aviso:** Dev A y Dev B crearon cada uno su propio `pyproject.toml`, `.gitignore`, `README.md` y `src/spaceapp/__init__.py`. Al unir las ramas habrá conflictos en esos archivos y hay que resolverlos a mano.
- **Verificación:** la copia se comparó con el origen (`diff -r`) y el commit se subió después con `git push origin dev-A` (`2d38c34..8ddbad7`). Las pruebas no se volvieron a ejecutar en el clon (no cambió ningún archivo de código).
- **Pendiente:** resolver los conflictos con `dev-B` al unir las ramas.


### B-015 · Fusión de `dev-B` en `dev-A` (solo en local)
- **Qué:** se trajo `origin/dev-B` (F0, F6 a F8, F12 y F13 de Dev B, con la interfaz web) a `dev-A` con `git merge`. `origin/test-B` ya contiene `dev-A` (PR #3), así que no aportó nada nuevo a esta fusión. **No se subió nada**: el commit de la fusión está solo en el equipo.
- **Resultado:** 115 archivos de Dev B entraron sin conflicto y hubo 5 conflictos de «agregar/agregar», resueltos así:

| Archivo | Resolución |
| --- | --- |
| `pyproject.toml` | Se conserva el de Dev A (hatchling, uv, reglas de lint y contratos de arquitectura) y se añade `pypdf>=5`, que necesita la ingesta de PDFs de Dev B |
| `.gitignore` | Unión de los dos |
| `knowledge/contracts.py`, `assistant/contracts.py` | Los eventos son `EventPayload` registrados (los exige el registro de eventos y su prueba de contratos). Se mantiene la copia local de `AlertRaised` de Dev B. `CitationDTO` pasa a ser un alias de `platform.vocab.Citation` (mismos campos y estados), así que el código de Dev B no cambió |
| `knowledge/facade.py` | La de Dev B (la mía era solo un esqueleto) |

- **Otros cambios por la fusión:**
  - `.github/workflows/ci.yml`: el trabajo de Python usaba `pip install -e ".[dev]"` y Python 3.14, que no funcionan con el `pyproject.toml` de Dev A. Ahora usa `astral-sh/setup-uv`, `uv sync --frozen` y `scripts/check.sh` con Python 3.12. El trabajo web no se tocó. Es un archivo compartido: Dev B debe revisarlo.
  - Se borró el `CODEOWNERS` de la raíz (marcadores de posición `@dev-a`/`@dev-b`). Manda el de `.github/` de Dev B, que sigue sin carpetas de Dev A.
- **Verificación** (`scripts/check.sh` en el árbol fusionado): ruff, mypy estricto, import-linter y **388 pruebas** (293 de Dev A y 95 de Dev B) con 97,22 % de cobertura. No se ejecutó la parte web (`npm`) ni el CI real en GitHub.
- **Pendiente:** subir la fusión (a `dev-A` o por PR hacia `testing`) cuando el usuario lo confirme; que Dev B revise el CI; completar el `CODEOWNERS` con las carpetas de Dev A; probar la interfaz web contra el backend.


### B-016 · Fusión de `origin/testing` en `dev-A` (solo en local)
- **Qué (pedido del usuario: «baja lo que se tiene en testing»):** `git fetch` y `git merge --no-ff origin/testing` en `dev-A`. `testing` traía el PR #4 (`integration/a-b`): Dev B integró `dev-A`, alineó los contratos de Conocimiento y Asistente con los de Dev A, cargó guía para las 25 reglas de Monitoreo, hizo la suscripción de Conocimiento al bus y ajustó el CI a `uv`.
- **Antes de fusionar:** había trabajo de F5 de una sesión anterior **sin commit ni entrada en la bitácora**. Se respaldó en el *scratchpad* de la sesión (`wip-f5.diff` y `wip-f5-untracked.tgz`) y en `git stash` («wip F5 realtime+graphql antes de fusionar testing»).
- **Conflictos (5), resueltos con la versión de `testing`**, porque Dev B ya los había integrado y probado en el PR #4:

| Archivo | Resolución |
| --- | --- |
| `.github/workflows/ci.yml` | La de `testing` (Python 3.12, `uv sync --frozen`, ruff, mypy, import-linter y pytest con cobertura por separado). Equivale a `scripts/check.sh` |
| `.gitignore` | La de `testing`: ya incluye las entradas de Dev A |
| `pyproject.toml` | La de `testing` (`pypdf` con comentario) |
| `knowledge/contracts.py`, `assistant/contracts.py` | Las de Dev B. Ya no hay copia local de `AlertRaised`: Conocimiento lee el contrato de Monitoreo |

- **Se mantiene de B-015:** el `CODEOWNERS` de la raíz sigue borrado (GitHub usa el de `.github/`).
- **Verificación** (`scripts/check.sh` sobre la fusión): ruff, mypy estricto, import-linter y **547 pruebas** (19 omitidas, de Dev B), con 97,27 % de cobertura.
- **No se subió nada.** `dev-A` queda con dos fusiones locales sin subir (B-015 y B-016).

### B-017 · F5: GraphQL, gateway `/ws` y prueba de extremo a extremo
- **Qué:** se recuperó el trabajo de F5 del *stash* (dominio de mensajes, hub con cola acotada, endpoint `/ws`, numeración y reenvío desde el outbox, y sus 32 pruebas, que ya pasaban) y se terminó la parte de GraphQL que estaba en RED.
- **Lo que se descartó del trabajo anterior:** mi adaptador de Conocimiento al bus (`KnowledgeEvents`), porque Dev B hizo el suyo en `testing` (`register_knowledge` con `HandleAlertRaised`). `main.py` usa ahora el de Dev B. También desapareció mi «omitir reglas sin guía»: Dev B cubre las 25 reglas y una regla desconocida reintenta.
- **Archivos nuevos:**

| Ruta | Contenido |
| --- | --- |
| `src/spaceapp/interfaces/graphql/schema.py` | Esquema Strawberry: `dashboard`, `alerts` (paginación por cursor, filtro por estado), `alert` (con regla y recomendación con citas), `rules`, `zoneReadings` (por minuto o cruda), `knowledgeSearch` y la mutación `acknowledgeAlert` con `union` de éxito y error (`NOT_FOUND`, `ALREADY_RESOLVED`). Límite de profundidad 10 |
| `src/spaceapp/interfaces/graphql/dashboard.py` | Signos vitales de la cabina, como función pura |
| `src/spaceapp/interfaces/graphql/context.py` | Servicios que recibe cada operación |
| `src/spaceapp/modules/realtime/...` | Del trabajo anterior: `domain/messages.py`, `application/hub.py`, `adapters/inbound/{ws,events}.py`, `adapters/outbound/sql.py`, puerto `OutboxReplay` |
| `tests/unit/graphql/test_dashboard.py`, `tests/unit/wiring/test_alert_to_recommendation.py`, `tests/integration/test_end_to_end.py` | Pruebas nuevas o reescritas |

- **Archivos cambiados:** `main.py` (Conocimiento de Dev B, `build_services`, hub suscrito al bus, `/graphql` y `/ws`), `monitoring/facade.py` (`AlertReadQuery` y `RuleQuery.all`), `telemetry/facade.py` (`TelemetryViews`: último valor por sensor y series), `pyproject.toml` y `uv.lock` (`strawberry-graphql`), `config.py` (`knowledge_catalog_path`), `tests/integration/graphql/test_schema.py` (dos expectativas corregidas, E-19 y E-20) y `docs/tareas-dev-a.md` (estado de F5).
- **Cómo se calcula un signo vital:** sin alertas es el promedio de las zonas y no lleva zona. Con alertas manda la peor: su severidad, su zona, el valor de esa zona y la evidencia de su regla. PIO₂ se deriva de la presión y el O₂. Una alerta de N₂ (sin signo propio) cuenta para la severidad global.
- **Prueba de extremo a extremo:** la app real con relay (LISTEN/NOTIFY), un cliente en `/ws` y un escenario de CO₂ en el laboratorio. La alerta llega con `seq`, se reconoce por `/graphql` y llega `alert.updated`. **Latencia de la alerta hasta el cliente: 47, 47 y 73 ms** en tres corridas (meta: 1 s). El tick más lento tardó entre 0,17 y 0,27 s en procesarse.
- **Verificación** (`scripts/check.sh`): ruff sin errores, mypy estricto sin errores en 149 archivos, 4 contratos de arquitectura cumplidos, **604 pruebas** (19 omitidas, de Dev B) y 96,96 % de cobertura.
- **TDD:** la prueba de cableado se reescribió primero y falló (RED: `cannot import name 'KnowledgeEvents'`). Las pruebas de GraphQL ya estaban en RED desde la sesión anterior (`No module named 'spaceapp.interfaces'`). Las de `dashboard.py` se escribieron antes que el código, pero **no se ejecutaron en RED** antes de escribirlo.
- **Decisiones:**
  - Severidades y estados salen en mayúsculas en GraphQL (`ALERTA`, `ACKNOWLEDGED`), como en el contrato de Dev B.
  - El hábitat se puede pedir por UUID o por código (`nave-transito`).
  - Las acciones se firman con un tripulante de demostración (`DEMO_CREW_MEMBER`) hasta que exista la selección de perfil.
  - Las recomendaciones viven en memoria (`InMemoryRecommendations` de Dev B): se pierden al reiniciar. La persistencia es de Dev B.
- **Pendiente de F5:** 5.4 (exportar `schema.graphql`, OpenAPI y `ws-messages.schema.json`, R8, `outboxStats` y limpieza de eventos de más de 24 h), `ping` del servidor cada 15 s, topics `habitat` y `crew`, DataLoaders y límite de costo, y las consultas de Tripulación.
- **Contrato con Dev B:** el esquema real incluye todo `contracts/schema.graphql` (lo comprueba `test_contract_superset.py`). Un cambio en ese archivo compartido necesita la revisión de Dev B.

### B-018 · F5, tarea 5.4: contratos exportados y operación del outbox
- **Commit previo:** el usuario pidió commit de B-017. Quedó en `9bed3c0` sobre `dev-A`, **sin subir**.
- **Qué:**
  - **Contratos para Dev B:** `python -m spaceapp.interfaces.contracts_export` escribe `contracts/schema.generated.graphql` (esquema completo), `contracts/openapi.json` (con el perfil `dev1`, para que salga R8) y `contracts/ws-messages.schema.json` (la ruta que ya cita `web/src/data/ws/types.ts`). Con `--check` falla si algo cambió. Una prueba exige que los archivos publicados coincidan con el código.
  - **El borrador `contracts/schema.graphql` de Dev B no se toca.** El usuario no contestó si se reemplazaba, así que se tomó la opción que no pisa nada. La prueba de subconjunto sigue vigente.
  - **R8** `POST /api/v1/admin/outbox/{id}:replay`: un evento `dead` vuelve a `pending` con cero intentos y se avisa al relay. Responde 404 si no existe y 409 si no está muerto. Solo en `dev1` y `dev2`.
  - **`outboxStats`** en GraphQL: pendientes, muertos y antigüedad del más viejo. En `jurado` devuelve null.
  - **Limpieza:** el relay borra cada 10 min los eventos `done` de más de 24 h (`purge_done`). Los muertos y los pendientes no se tocan. El inbox no se limpia: si se limpiara, reencolar un muerto viejo repetiría consumidores que ya lo procesaron.
  - **`ping` del servidor** en `/ws` tras 15 s sin mensajes.
  - **Catálogo de mensajes:** `SERVER_TYPES` (tipo → topic) y `SYSTEM_TYPES` en el dominio de realtime. Las pruebas exigen que cada evento traducido produzca un tipo publicado en su topic y que todo tipo publicado tenga un evento que lo produzca.
- **Archivos nuevos:** `src/spaceapp/platform/outbox/admin.py`, `src/spaceapp/interfaces/rest/admin.py`, `src/spaceapp/interfaces/contracts_export.py`, `src/spaceapp/modules/realtime/adapters/inbound/ws_schema.py`, los tres archivos de `contracts/`, `tests/integration/test_outbox_admin.py`, `tests/unit/realtime/test_ws_schema.py` y `tests/unit/test_contracts_export.py`.
- **Archivos cambiados:** `platform/outbox/{__init__,relay}.py`, `realtime/domain/messages.py`, `realtime/adapters/inbound/ws.py`, `interfaces/graphql/{context,schema}.py`, `main.py` y `tests/unit/realtime/test_ws_endpoint.py`.
- **TDD:** cada parte empezó en RED (`cannot import name 'purge_done'`, falta `ping_interval`, falta `ws_schema` y falta `contracts_export`). Una prueba miraba `app.routes`, pero esta versión de FastAPI no aplana los routers incluidos. Se cambió por las rutas del OpenAPI.
- **Verificación** (`scripts/check.sh`): ruff sin errores, mypy estricto sin errores en 154 archivos, 4 contratos de arquitectura cumplidos, **623 pruebas** (19 omitidas, de Dev B) y 97,04 % de cobertura.
- **Pendiente de F5** (depende de otras fases): consultas de Tripulación (`crewMember`, `recordBaseline`, `setConsent`), topics `habitat` (F4) y `crew`, DataLoaders y límite de costo.

### B-019 · F4: nave, zonas e incidencias
- **Commit previo:** 5.4 quedó en `81686a1` (sin subir).
- **Qué:** una alerta de Alerta o más en una zona abre un ticket con tipo, descripción, severidad y ubicación, y la zona toma su color en la misma transacción. GraphQL, WebSocket y contratos incluidos.
- **Datos (generados una vez desde `tools/docgen`):**
  - `data/facility/plan.json`: las 10 zonas, con los mismos códigos que el simulador y la geometría del artefacto. Todo `DEMO`.
  - `data/facility/incident_types.json`: 61 tipos y 12 categorías. Cada tipo AUTO lleva sus **claves de regla exactas**. En `ITYPES` había familias (`env-pio2` valía para hipoxia y para hiperoxia). Las 20 reglas que aún no existen van en `pending_rules`.
- **Reglas del dominio** (`facility/domain/incidents.py`, funciones puras): Atención no abre ticket. Hay un solo ticket automático abierto por zona: si llega otra alerta se anota y, si es peor, se escala (`incident_updated`). Cuando se resuelve la última alerta, el ticket queda marcado como «valores normales» pero **no se cierra solo**. Un ticket automático no se puede cerrar con alertas activas en su zona; uno manual sí. El color de la zona es la peor severidad entre alertas activas y tickets abiertos, y solo se publica cuando cambia.
- **Persistencia:** migración `migrations/facility` (`habitat`, `zone`, `zone_alert`, `incident` con índice único parcial de un ticket automático abierto por zona, e `incident_update`).
- **Arranque:** la primera vez que el proceso necesita Nave (un evento, una consulta o una mutación), sincroniza el plano y reconstruye la proyección de alertas activas y el color de cada zona desde `ActiveAlertsQuery` de Monitoreo.
- **GraphQL** (fragmento propio, `interfaces/graphql/facility.py`, compuesto con `merge_types`; los tipos compartidos pasaron a `common.py`): `ship`, `incidents` (cursor y filtros por estado y zona), `incident` (con su tipo y su historial), `incidentTypes(category)`, `reportIncident`, `acknowledgeIncident` y `resolveIncident`, con errores tipados (`NOT_FOUND`, `ALREADY_RESOLVED`, `ACTIVE_ALERTS`, `UNKNOWN_ZONE`, `UNKNOWN_TYPE`, `INVALID_SEVERITY`).
- **WebSocket:** topic nuevo `habitat` con `incident.opened`, `incident.updated`, `incident.resolved` y `zone.status`, todos con `seq` para reanudar.
- **Verificación** (`scripts/check.sh`): ruff sin errores, mypy estricto sin errores en 165 archivos, 4 contratos de arquitectura cumplidos, **662 pruebas** (19 omitidas, de Dev B) y 96,84 % de cobertura. La prueba de extremo a extremo comprueba además que un cliente que se suscribe tarde recupera con `resume` el ticket y el color del laboratorio, en orden y sin duplicados. Latencia de la alerta: 63 ms.
- **Criterios de aceptación de F4,** todos con prueba: una alerta abre exactamente un ticket y pinta la zona; una segunda alerta no abre otro; un ticket automático con valores fuera de rango no se resuelve; cambiar el plano cambia las zonas de `ship`; al reiniciar se reconstruye el estado de las zonas.
- **TDD:** el dominio, las pruebas de los mensajes WebSocket y la del exportador empezaron en RED. **El servicio de aplicación, el repositorio SQL y el GraphQL se escribieron antes que sus pruebas de integración.** Para comprobar que esas pruebas detectan errores se hizo una mutación: con el bloqueo de cierre desactivado, la prueba falla.
- **Hallazgo en los datos:** la validación del catálogo encontró reglas futuras compartidas entre tipos (`power-bus` en dos, `sensor-health` en tres). Se separaron (`power-bus-fault`, `power-bus-low`, `sensor-health-down`, `-calibration` y `-dosimeter`).
- **Diferencias con el plan:** no hay tabla `incident_type` (el catálogo se carga en memoria, como el plano); hay una tabla nueva, `zone_alert`; `typicalZones` devuelve códigos de zona (`*` = cualquiera), mientras el mock de Dev B usa nombres; no hay DataLoaders.
- **Riesgo:** con Nave conectada, el tick más lento de la prueba de extremo a extremo subió de 0,27 a 0,64 s (incluye la reconstrucción inicial). Sigue bajo 1 s.

### B-020 · Revisión del remoto (15 de noviembre, 02:30)
- **Qué:** `git fetch --all --prune` y comparación de ramas, sin cambiar nada del repositorio.
- **`dev-A`:** 21 commits por delante de `origin/dev-A` y ninguno subido. Incluye las fusiones B-015 y B-016, F5, 5.4 y F4.
- **`testing`:** sin cambios desde el PR #4 (`880c416`), que ya está fusionado en `dev-A`.
- **`dev-B`:** 14 commits nuevos que todavía no están en `testing`:
  - interfaz de F10 (tareas del día) y F11 (panel de Tierra), contra mocks (`web/src/data/mocks/tasks.ts`);
  - F14 (voz con Whisper en Docker);
  - asistente con n8n y Ollama (fases 1 a 6), más `src/spaceapp/devtools/`.
- **Dev B no tocó carpetas de Dev A.** Fuera de su zona solo cambió `.gitignore` y una excepción de mypy para `faster_whisper` en `pyproject.toml`. `n8n/credentials/ollama.json` solo trae una URL, sin secretos.
- **Merge de prueba** (`git merge-tree dev-A origin/dev-B`): sin conflictos.
- **PRs** (API pública de GitHub; `gh` no está instalado): #1 cerrado, y #2, #3 y #4 fusionados. No hay PRs abiertos.
- **Pendiente de lo propuesto al usuario:** subir `dev-A`, abrir el PR hacia `testing`, revisar el CI real y hacer F9. Nuevo: el backend de F10 y F11 (de Dev A) es lo que espera la interfaz que Dev B ya hizo.
- **Decisión que registró Dev B** (bitácora E18): n8n es obligatorio para el asistente. Eso responde la pregunta abierta 2 de la sección 2.3; falta que el usuario la confirme.

### B-021 · Push de `dev-A` a GitHub
- **Qué (pedido del usuario):** `git push origin dev-A` (`9fb8bfe..1db03f4`). Subieron los 22 commits: las fusiones B-015 y B-016 (con los commits de Dev B que traen), F5 (`9bed3c0`), 5.4 (`81686a1`), F4 (`286024c`) y la bitácora B-020 (`1db03f4`). Después se subió este registro.
- **Verificación:** `git rev-list --left-right --count dev-A...origin/dev-A` → `0 0`.
- **Pendiente:** abrir el PR `dev-A → testing` (`gh` no está instalado: se crea desde la web), que Dev B abra el suyo `dev-B → testing` y revisar el CI de GitHub.

### B-022 · F10 y F11: tareas del día y plan desde Tierra (backend)
- **Pedido del usuario:** dejar F9 para cuando la interfaz esté lista y hacer mientras tanto el backend de F10 y F11.
- **Alineado con la interfaz de Dev B** (`origin/dev-B`: `features/tasks/model.ts` y `features/ground/model.ts`): mismos tipos, orígenes, estados, `blockedReason`, `effective` y `sourceAlertId`, y las etapas del plan EN_COLA → EN_EL_ENLACE → RECIBIDO → APLICADO → CONFIRMADO.
- **F10, módulo `engagement`:**
  - **Tareas del día:** cada plantilla activa da una tarea por día, sin duplicados. Siete plantillas del sistema de demostración en `data/engagement/templates.json`: tres rutinas de salud y cuatro tareas de nave, tomadas del artefacto.
  - **Tareas propias:** la tripulación crea, edita y borra las suyas (SALUD o NAVE). Las de Tierra y las del sistema devuelven `NOT_EDITABLE` o `NOT_DELETABLE`. Toda tarea se puede completar (con `effective`), posponer o bloquear con motivo; bloquear no la borra.
  - **Handlers:** un ticket abierto crea una tarea INCIDENTE y su resolución la completa. Cada acción de una recomendación es una medida del día con `sourceAlertId`, que no suma a la racha. Todo es idempotente (índices únicos parciales).
  - **Racha:** solo cuentan las rutinas de salud completadas; no suman ni Tierra, ni incidentes, ni alertas.
  - **Aplicar un plan de Tierra** (una transacción): NEW, UPDATE y CANCEL sobre plantillas de origen TIERRA. Un ítem inválido se rechaza solo él, con motivo. Tierra no toca plantillas locales, y una versión repetida o menor se ignora. Lo completado o creado a bordo se conserva y la cancelación rige para el futuro. Publica `ground_plan_applied` con lo aplicado y lo rechazado.
- **F11, módulo `groundlink`:**
  - **Nave (R9, `POST /api/v1/groundlink/inbound/plans`):** valida la integridad (SHA-256 del JSON canónico de versión e ítems) y la forma de cada ítem. Un plan corrupto se rechaza completo con 422 y se puede reenviar corregido con el mismo lote. Una versión repetida o menor responde 200 `ignored`; una nueva, 202, y publica `ground_plan_received`. Cuando Misiones aplica el plan, se marca y se confirma (`batch_acknowledged`).
  - **Tierra (demo):** un borrador, publicación con versión siguiente, una sola publicación en curso, y un enlace simulado con demora y corte (R5 `PUT /api/v1/groundlink/link` y `setGroundLink`). Con el enlace cortado el plan queda EN_COLA y sale al volver; si se corta en vuelo, vuelve a la cola; la confirmación también espera al enlace.
- **GraphQL** (fragmento `interfaces/graphql/missions.py`): `tasks(day, kind, status)`, `streak`, `groundPlan`, `createTask`, `updateTask`, `deleteTask`, `completeTask`, `blockTask`, `snoozeTask`, `groundControl`, `saveGroundTemplate`, `cancelGroundTemplate`, `publishGroundPlan` y `setGroundLink`, con errores tipados.
- **WebSocket:** topic nuevo `crew` con `task.assigned`, `task.created`, `task.completed`, `task.blocked`, `groundplan.received`, `groundplan.applied`, `groundplan.confirmed` y `groundlink.state`.
- **Migraciones:** `migrations/engagement` y `migrations/groundlink`. Contratos regenerados.
- **Verificación** (`scripts/check.sh`): ruff sin errores, mypy estricto sin errores en 182 archivos, 4 contratos de arquitectura cumplidos, **707 pruebas** (19 omitidas, de Dev B) y 95,89 % de cobertura. Hay una prueba por HTTP sobre la app real (relay encendido y enlace con 0,1 s de demora): Tierra publica, la nave aplica, Tierra ve CONFIRMADO y la tripulación ve la tarea.
- **Criterios de aceptación de F10 y F11,** todos con prueba: tarea propia sin enlace; tarea de incidente completada al resolver el ticket; editar o borrar una tarea de Tierra da error tipado; `effective` sale en `task_completed`; plan en cola con el enlace cortado que llega, se aplica y se confirma al volver; el mismo plan dos veces deja las tareas una vez; lo completado o creado a bordo no se pierde. También las ocho reglas de conflicto de la sección 13.11.
- **TDD:** los dominios de `engagement` y `groundlink` y los mensajes WebSocket empezaron en RED. **Los servicios, los repositorios y el GraphQL se escribieron antes que sus pruebas de integración.** Se hizo una mutación de control: sin la comprobación de versión repetida, la prueba de idempotencia falla.
- **Error corregido en el camino:** al rechazar un plan corrupto se guardaba su lote, y eso bloqueaba el reenvío corregido con el mismo `batch_id`. Lo detectó la prueba de R9 y se arregló con un `ON CONFLICT ... WHERE status = 'RECHAZADO'`.
- **Diferencias con el plan:**
  - sin tablas de recordatorios ni de logros;
  - `snoozeTask` en vez de `snoozeReminder`;
  - el panel de Tierra no filtra por consentimiento (no existe aún el módulo de Tripulación) ni autentica el rol `ground`;
  - Tierra comparte base con la nave en la demo;
  - todas las tareas son del tripulante de demostración.
- **Para Dev B:** cambiar los mocks de tareas y del panel de Tierra por estas operaciones y por el topic `crew`. La vista `groundControl` sigue la forma de su `GroundState` (`appliedVersion`, `templates`, `draft`, `published.stage` y `link`).

---

## 4. Archivos del proyecto por área

| Área | Ubicación | Creado por |
| --- | --- | --- |
| Documentos de contexto | `docs/spaceapps-health-monitor-context.md`, `docs/spaceApps 4186…md` | Usuario |
| Plan de arquitectura | `docs/plan-arquitectura.md` | Asistente (generado) |
| Tareas de Dev B | `docs/tareas-dev-b.md` | Asistente |
| Informe TDD F0 y F1 | `docs/tdd/f0-f1.tdd.md` | Asistente |
| Bitácora | `docs/bitacora.md` | Asistente |
| Tareas de Dev A | `docs/tareas-dev-a.md` | Asistente |
| Generador del plan y del artefacto | `tools/docgen/` | Asistente (movido desde el *scratchpad*) |
| Backend de Dev A (Bloques 1 y 2) | `src/`, `tests/`, `migrations/`, `docker/`, `scripts/`, `rules/`, `data/` | Asistente |
| GraphQL compuesto (F5) | `src/spaceapp/interfaces/graphql/` | Asistente |
| Nave e incidencias (F4) | `src/spaceapp/modules/facility/`, `migrations/facility/`, `data/facility/` | Asistente |
| Tareas y plan desde Tierra (F10, F11) | `src/spaceapp/modules/engagement/`, `src/spaceapp/modules/groundlink/`, `migrations/{engagement,groundlink}/`, `data/engagement/` | Asistente |
| Contratos generados para Dev B | `contracts/schema.generated.graphql`, `contracts/openapi.json`, `contracts/ws-messages.schema.json` | Asistente (generados) |
| Informes de evidencia TDD | `docs/tdd/f0-f1.tdd.md`, `docs/tdd/f2-f3.tdd.md` | Asistente |

---

## 5. Cambios fuera del repositorio

Todo lo que se hizo en el equipo del usuario, para poder revertirlo.

| Cambio | Detalle | Cómo revertir |
| --- | --- | --- |
| Servicio `docker-desktop` iniciado | Servicio de usuario arrancado con `systemctl --user start`. **No se habilitó** para el inicio | `systemctl --user stop docker-desktop` |
| `uv` 0.13.8 instalado | En `~/.local/bin/uv`. Descargado de los *releases* oficiales de `astral-sh/uv` con SHA-256 verificado | Borrar `~/.local/bin/uv` |
| Python 3.12.16 descargado | Por `uv`, en `~/.local/share/uv/python/` | `uv python uninstall 3.12` |
| Imagen `pgvector/pgvector:pg16` descargada | Para las pruebas de integración y el compose | `docker rmi pgvector/pgvector:pg16` |
| Entorno virtual del proyecto | `.venv/` dentro del repositorio | Borrar `.venv/` |
| Contenedor `spaceapp-postgres-1` y su volumen | Creados para la prueba real y **eliminados** al terminar | Ya revertido |
| Contenedores de testcontainers | Efímeros, eliminados al terminar las pruebas | Ya revertido |
| Servidores locales de vista previa | Puertos 8765 a 8768 y 8010, detenidos | Ya revertido |
| Prueba en vivo del Bloque 2 | Contenedor `spaceapp-postgres-1` y su volumen, y la aplicación en el puerto 8011. Detenidos y eliminados al terminar | Ya revertido |
| Repositorio clonado | `~/Documentos/SpaceOverflow` (clon de `Julio-Cuellar/SpaceOverflow`, rama `dev-A` con el trabajo de Dev A, ya subida a GitHub) | Borrar la carpeta `~/Documentos/SpaceOverflow` |
| Fusiones locales en `dev-A` | B-015 (`dev-B`) y B-016 (`origin/testing`), **sin subir** | `git reset --hard origin/dev-A` (descarta las dos fusiones y el trabajo sin commit) |
| `git stash` en el clon | «wip F5 realtime+graphql antes de fusionar testing». Ya se reaplicó: se puede borrar | `git stash drop` |
| Respaldo del trabajo de F5 | `wip-f5.diff` y `wip-f5-untracked.tgz` en el *scratchpad* temporal de la sesión | Se borra solo con la sesión |
| `strawberry-graphql` 0.341.2 | En el `.venv` del clon, por `uv sync` | `uv sync` sin la dependencia |

**No se tocó:** los contenedores de otro proyecto del usuario (`clinerya-postgres`, `clinerya-backend`, `clinerya-frontend`, `clinerya-rabbitmq`).

**Observación:** el artefacto figura como «Cualquiera con el enlace». Esa configuración no la cambió el asistente.

---

## 6. Errores y correcciones

| # | Qué pasó | Cómo se corrigió |
| --- | --- | --- |
| E-1 | Dije que el corte P0 eran 41 h. Son 40 h | Corregido en el mensaje siguiente y en el plan (calculado desde los datos) |
| E-2 | Llamé `uplink` al módulo que envía datos a Tierra, y en operaciones espaciales eso es el *downlink* | Renombrado a `groundlink` en el documento, el artefacto y el código |
| E-3 | Una primera versión del informe TDD traía 4 conteos de pruebas por archivo mal | Se contrastaron con `pytest --collect-only` y se corrigieron |
| E-4 | Una prueba mía escribió en el campo equivocado del formulario de Tierra | Fue un error del *script* de prueba, no del producto. Se repitió con el campo correcto |
| E-5 | Dos veces, `pkill -f` detuvo mi propio shell (código 144) porque el patrón coincidía con la propia orden | Se usó un filtro con `awk` que excluye al propio proceso. No dejó nada a medias |
| E-6 | `import-linter` falló por patrones `ignore_imports` sin coincidencias | `unmatched_ignore_imports_alerting = "none"` |
| E-7 | mypy estricto dio 16 errores | Corregidos sin relajar el modo estricto (ver informe TDD) |
| E-8 | El puerto 5432 estaba ocupado por otro proyecto | La base de este proyecto usa 5433 |
| E-9 | `make` no está instalado | Se añadió `scripts/check.sh` |
| E-10 | En el navegador integrado, algunas capturas salieron en blanco y el texto con acentos salió roto | Es un efecto del servidor de vista previa (sin `charset`) y de la captura. No afecta a lo publicado |
| E-11 | La tercera prueba del generador solo comprobaba que `stderr` estuviera vacío, así que no probaba nada útil | Se reemplazó por una prueba que exige que un marcador desconocido haga fallar la generación y se nombre |
| E-12 | En `tareas-dev-a.md` las subtareas de F2 sumaban 4,25 h y la fase es de 4 h | Se redujo la subtarea 2.2 a 0,75 h y se verificaron las sumas de todas las fases |
| E-13 | Una expectativa mía del handler estaba mal: con la ventana escalada de la prueba, PIO₂ de 121 mmHg cumple el límite absoluto (122) | Se corrigió la prueba, no el motor |
| E-14 | El detector de tendencia exigía 20 puntos de línea base, pero la atmósfera se muestrea cada 5 s: nunca habría disparado. Lo mostró el diseño del simulador | Prueba primero (RED), y parámetros de ventana por regla en el catálogo |
| E-15 | La regla de velocidad de presión usaba 60 s de ventana: una fuga real promedia unos 6 psi/min y no llegaba a 13,5 | Prueba primero y ventana de 10 s |
| E-16 | Mi caso de prueba de la fuga evaluaba el segundo 30, donde el cambio en 10 s es 0,97 psi y la regla lo exime por correcto diseño | Se corrigió el caso y se añadió una prueba que documenta la exención |
| E-17 | 19 pruebas de integración fallaban a la vez: un reemplazo de texto en `conftest.py` no se aplicó porque `ruff format` ya había reformateado la lista | Se editó sobre el texto real |
| E-18 | Otro reemplazo de texto (en el motor) tampoco se aplicó por lo mismo, sin avisar | Se detectó con `grep` y se aplicó. Lección: comprobar cada reemplazo masivo |
| E-19 | Una prueba de GraphQL de la sesión anterior esperaba que no hubiera alertas resueltas tras el escenario de CO₂. La pre-alerta se resuelve al quedar reemplazada por la alerta (`supersedes`) | Se corrigió la prueba, no el código: ahora exige que las resueltas sean de otras reglas |
| E-20 | Otra prueba esperaba 20 muestras de presión crudas en 30 s, pero la prueba avanza la simulación de 5 en 5 s (7 muestras) | Se corrigió la prueba: exige una muestra por tick |
| E-21 | La primera medición de latencia de extremo a extremo (1,9 s) estaba mal: leía el socket después de todos los ticks y metía 330 s simulados en 5 s de reloj, así que la alerta esperaba detrás de lecturas posteriores | La prueba lee en paralelo y avanza a ritmo real (un tick cuando el relay terminó el anterior). Medido: 47 a 73 ms |
| E-22 | El trabajo de F5 de una sesión anterior quedó sin commit y sin entrada en la bitácora | Se registró en B-017. Lección: cerrar cada sesión con la entrada de la bitácora aunque el bloque no esté terminado |

---

## 7. Riesgos de mantenimiento

1. ~~Los generadores del plan y del artefacto vivían en una carpeta temporal.~~ **Resuelto en B-011.** La fuente está en `tools/docgen/` y una prueba falla si `docs/plan-arquitectura.md` deja de coincidir con ella.
2. ~~Faltaba un documento propio para Dev A.~~ **Resuelto en B-012:** `docs/tareas-dev-a.md`.
3. **El artefacto publicado se actualiza a mano.** El generador crea `tools/docgen/out/plan.html`, pero publicarlo sobre el mismo enlace es un paso manual. Si cambian los datos, el artefacto queda desfasado hasta que se republique.
4. **El plan sigue sin confirmación formal.** La ejecución se apoya en el «ejecuta» del usuario para el Bloque 1.
5. **Sin commits.** Hasta que se haga el primero, el historial solo vive en esta bitácora y en los informes TDD.
6. **Tres secciones del plan dependen de decisiones abiertas** (RAG, n8n y F12). Dev B puede avanzar con los supuestos de la sección 2.2.
7. **Las horas de `crew` no tienen una fase asignada** (línea base y consentimientos). En F2 no hizo falta nada de `crew`. Queda para F15 y para cuando haya reglas relativas a la línea base.
8. ~~Falta un evento de escalada de severidad.~~ **Resuelto en el Bloque 2:** cada regla tiene severidad fija y subir de nivel es resolver y levantar. Queda por acordar con Dev B si el gateway mapea `alert.updated` al reconocimiento.
9. **Rendimiento de Monitoreo con ventanas reales.** Con 1 h de ventana consulta unas 3.600 lecturas por métrica y zona en cada lote. No se midió. `rollup_mean` ya existe como alternativa.
10. **El hito I2 depende del gateway (F5).** B sigue con sus grabaciones hasta I5.
11. **El artefacto publicado quedó desfasado** respecto al modelo de datos regenerado (reglas, alertas y escenarios tienen columnas nuevas). Falta republicarlo.

---

## 8. Cómo comprobar el estado actual

```bash
cd /home/julio_jcode/Documentos/space_apps
scripts/check.sh                                              # ruff, mypy, import-linter y pytest con cobertura
docker compose -f docker/compose.yaml up -d --wait postgres   # base local en el puerto 5433
uv run python -m spaceapp.platform.migrate platform           # migraciones
uv run uvicorn --factory spaceapp.main:create_app             # API: /health y /ready
uv run python tools/docgen/build.py --artifact-url <URL>      # regenera el plan y la página interactiva
```

Las pruebas de integración necesitan Docker en marcha (`systemctl --user start docker-desktop`).

---

## 9. Próximos pasos

1. **F9 (entrega al jurado):** Dockerfile, compose completo con perfil `jurado` y migraciones de todos los módulos al arrancar. Después F10 (tareas) y F11 (plan desde Tierra).
2. **Subir `dev-A`** (dos fusiones locales y F5) cuando el usuario lo pida, directo o por PR hacia `testing`.
3. **Revisión de contratos por Dev B (I0):** `contracts.py` de cada módulo, `event_registry.py` y el bus en memoria.
4. **Republicar el artefacto** para reflejar el modelo de datos actual (decisión del usuario).
5. **Decisiones pendientes** de la sección 2.3.
6. **Avisar a Dev B** de los contratos generados, de que `schema.graphql` sigue siendo su borrador, del topic nuevo `habitat` y de que `typicalZones` trae códigos de zona.
