# Bitácora del proyecto

> NASA Space Apps 2026 · monitor de salud para astronautas
> Registro cronológico de lo que se hace y de cada cambio que se produce, incluidos los que se hacen **fuera del repositorio** (instalaciones, servicios) y los errores corregidos.
> Última actualización: 14 de noviembre de 2026, 23:30.

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
| Código | **Bloques 1 y 2 de Dev A terminados** (F0 a F3). **F5 casi terminada**: GraphQL con las consultas de Monitoreo, Telemetría y Conocimiento, gateway `/ws` y prueba de extremo a extremo. F4 sin empezar. El trabajo de Dev B (F0, F6 a F8, F12, F13) ya está integrado desde `testing` |
| Pruebas | **604 pasan y 19 se omiten** (las omitidas son de Dev B), 96,96 % de cobertura, ruff y mypy estricto sin errores, 4 contratos de arquitectura cumplidos |
| Artefacto interactivo | Versión 4 publicada: https://claude.ai/artifact/LMrTxLRghTr9h3v2Q79am8 |
| Repositorio git | El trabajo vive en `~/Documentos/SpaceOverflow`, rama `dev-A`. Dos fusiones **solo en local** (B-015 y B-016). El trabajo de F5 está **sin commit** |
| Siguiente bloque propuesto | Terminar F5 (5.4, contratos exportados) y hacer F4 (nave, zonas e incidencias), con su GraphQL. Cierra I3 e I5 |

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

1. **Terminar F5 (5.4) y hacer F4:** exportar los contratos para Dev B. Después, plano e incidencias (tickets automáticos desde las alertas por zona, catálogo de 61 tipos, estado de color de cada zona) con su GraphQL y sus mensajes WebSocket. Cierra I3 e I5.
2. **Subir `dev-A`** (dos fusiones locales y F5) cuando el usuario lo pida, directo o por PR hacia `testing`.
3. **Revisión de contratos por Dev B (I0):** `contracts.py` de cada módulo, `event_registry.py` y el bus en memoria.
4. **Republicar el artefacto** para reflejar el modelo de datos actual (decisión del usuario).
5. **Decisiones pendientes** de la sección 2.3.
6. **Commit de F5** cuando el usuario lo pida.
