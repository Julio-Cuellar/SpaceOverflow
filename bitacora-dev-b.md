# Bitácora de Dev B · monitor de salud para astronautas

> Registro de lo que se hace, cómo y con qué evidencia. Plan de referencia: `/home/juls_d3v/Descargas/tareas-dev-b.md` (con `plan-arquitectura.md` y `spaceapps-health-monitor-context.md`).
> Entradas en orden cronológico. Nunca se borran: si algo cambia, se añade una entrada nueva que lo corrige.

## Cómo se trabaja (método)

- **TDD por tarea:** RED (prueba escrita y ejecutada, falla por la razón esperada) → GREEN (implementación mínima, la misma prueba pasa) → REFACTOR (sin cambiar comportamiento, pruebas en verde) → cobertura.
- **Evidencia:** cada ciclo registra el comando exacto y un extracto de la salida. Lo que no se ejecutó se marca como no verificado.
- **Git:** desde E08 el proyecto es un repositorio (`origin`: `Julio-Cuellar/SpaceOverflow`) y el trabajo de Dev B vive en la rama `dev-B`. Hasta E07 no hubo commits; la evidencia de esos cortes está en esta bitácora. De E08 en adelante se hace un commit por fase o corte.
- **Estados:** `HECHO` (verificado con evidencia), `PARCIAL` (algo quedó fuera, con motivo), `PENDIENTE`, `BLOQUEADO` (depende de Dev A o de una decisión).
- **Regla de honestidad del proyecto:** todo dato sin fuente verificada va marcado `DEMO`. El modelo de lenguaje nunca decide una alerta.

## Mapa de fases y estado

| Fase | Tema | Estado | Nota |
| --- | --- | --- | --- |
| F0 | Cimientos (web, codegen, mocks) | PARCIAL | Hecho: web, pruebas, codegen, mocks, borrador de contrato, CODEOWNERS y CI (el CI aún no se ha ejecutado en GitHub). Falta congelar el contrato con Dev A (I0) |
| F8 | Conocimiento con datos de demo | PARCIAL | Dominio, caso de uso idempotente, catálogo DEMO, fachadas y búsqueda de pasajes probados (29 pruebas). Falta persistencia y outbox de A |
| F6 | Interfaz de cabina | PARCIAL | Semáforo, tarjetas, cuerpo humano, gráficas SVG con umbral y anomalía, estado de espera, panel de alerta y cola WS, todo cableado en `App` con datos de demostración. Falta el hook `useWs` conectado a `/ws` (I2) y la tendencia de CO₂ en la cabina |
| F7 | Panel de la nave | PARCIAL | Plano desde `zone.layout`, pins de ticket, orden y regla de «resolver», gráficas por zona con pausa, formulario de reporte, catálogo filtrable y modo demo por perfil. Falta el catálogo completo de 61 tipos y el backend |
| F12 | RAG sobre PDFs de NASA | PARCIAL | Manifiesto con licencias, fragmentación por requisito, lectura de PDF, ingesta idempotente, búsqueda con glosario es→en, respaldo a demo y evaluación, probados con PDFs sintéticos y luego con los 7 PDFs reales (2 087 fragmentos, E10). **Recuperación por debajo del umbral del plan:** 56 % en el conjunto principal, 11 % en el retenido, 0 respuestas sin fuente. Faltan el buscador de pasajes en la web (12.6) y la decisión del modelo de embeddings |
| F13 | Asistente texto y Ollama | PARCIAL | Backend: caso de uso con límite de 8 s, adaptadores nulo y Ollama, evento `answer_ready` (15 pruebas). Web: pestaña Asistente con datos de demostración. Falta GraphQL, persistencia SQL, Ollama real probado y n8n opcional |
| F14 | Voz con Whisper | PENDIENTE | |
| F9 | Entrega (Docker, sin internet) | PENDIENTE | conjunta con A |
| F10 | Tareas (interfaz) | PENDIENTE | |
| F11 | Panel del centro de control | PENDIENTE | |
| F16 | Alexa como respaldo | PENDIENTE | solo si Whisper se traba |

---

## Entradas

### 2026-11-14 · E01 · Preparación del entorno

- **Qué:** se revisó el directorio de trabajo (estaba vacío). Se creó la estructura `web/`, `contracts/`, `data/knowledge/`, `src/spaceapp/modules/knowledge/` y `tests/knowledge/`.
- **Herramientas detectadas:** Node 24.22.1, npm 11.19.1, Python 3.14.4. `uv` no está instalado; se usará `venv` de Python. El registro de npm y de pip responde.
- **Web instalada:** react 18, react-dom 18, urql, graphql, uplot (dependencias); vite, @vitejs/plugin-react, typescript, vitest 3, jsdom, @testing-library/react 16, jest-dom, user-event, msw, @graphql-codegen/cli y client-preset (desarrollo).
- **Desvío:** `esbuild` mostró un aviso de `install-scripts` de npm 11. Se revisará al primer `vite build`.
- **Contratos:** el plan dice que el esquema GraphQL y los mensajes WS se congelan en I0 junto con Dev A. Dev A todavía no entregó nada. Se redactará un **borrador** en `contracts/`, marcado como pendiente de revisión, para que B pueda generar tipos y mocks.
- **Estado:** PARCIAL. Entorno listo; faltan configuración y pruebas.

### 2026-11-14 · E02 · F0 cimientos de la interfaz (TDD)

**Ciclo RED → GREEN, primera pasada**

- **RED:** se escribieron 6 suites (severidad, SevPill, EvidenceBadge, Banner, reproductor WS, dashboard de ejemplo). Comando: `npx vitest run`. Resultado: `Test Files 6 failed (6)`, causa `Failed to resolve import "./SevPill"` y similares. Falló por módulo inexistente, que es el fallo esperado.
- **GREEN:** se implementó lo mínimo: `shared/lib/severity.ts`, `shared/lib/evidence.ts`, `shared/ui/{SevPill,EvidenceBadge,Banner}.tsx`, `data/ws/{types,replay}.ts`, `data/mocks/fixtures.ts`. Resultado: `Tests 19 passed (19)`.
- **Desvíos corregidos durante GREEN:**
  1. Faltaba `tsconfig.json` con `jsx: react-jsx`. Sin él, Vitest fallaba con `React is not defined`.
  2. Testing Library no limpiaba el DOM entre pruebas, porque Vitest no expone globals. Se añadió `cleanup()` en `src/test/setup.ts`.
  3. Faltaba `@vitest/coverage-v8`. Se instaló.

**Ciclo RED → GREEN, segunda pasada (contrato, mock y punto de entrada)**

- **RED:** `contract.test.ts` (documento `dashboard` contra el esquema), `handlers.test.ts` (MSW responde `Dashboard`), `recordings.test.ts` (grabación con `telemetry.tick`), `App.test.tsx` (banner al abrir). Resultado: `4 failed`, 19 pasaban.
- **GREEN:** `contracts/schema.graphql` (borrador), `web/src/data/graphql/documents/dashboard.graphql`, `data/mocks/handlers.ts`, `data/mocks/ws/recordings.ts`, `App.tsx`, `main.tsx`, `index.html`, `shared/tokens.css`, `codegen.ts`. Resultado: `Tests 26 passed (26)`.
- **Desvío:** `import.meta.url` no es una ruta `file://` en el entorno jsdom. El test de contrato resuelve la ruta desde `process.cwd()` (siempre `web/`).

**Verificación de criterios de aceptación de F0**

| Criterio | Evidencia |
| --- | --- |
| `npm run dev` abre con banner | `App.test.tsx` lo comprueba en jsdom. Falta revisar en navegador (ver pendientes) |
| `npm run codegen` genera tipos | `npm run codegen` → `✔ Generate outputs` |
| Mock devuelve `dashboard` | `handlers.test.ts` pasa con MSW |
| Reproductor emite `telemetry.tick` | `recordings.test.ts` y `replay.test.ts` pasan |
| Esquema congelado (I0) | **No**: el borrador está pendiente de revisión de Dev A |

**Cobertura y build:**

- `npx vitest run --coverage` → líneas 91,89 %, funciones 100 %, ramas 81,25 %, sentencias 89,47 %. Supera el umbral de 80 %.
- `npx tsc --noEmit` → sin errores (exit 0).
- `npx vite build` → `✓ built in 154ms`, bundle 140,92 kB (gzip 45,83 kB).

**Decisiones de B (no vienen tal cual del plan):**

1. **Cuatro niveles de severidad con símbolo propio:** `● Normal`, `▲ Atención`, `◆ Alerta`, `■ Crítico`. El plan dice el símbolo para Normal, Atención y Crítico, pero no para Alerta. Se eligió ◆ para que cada nivel tenga una forma distinta.
2. **CO₂ alto da `ALERTA`, que se muestra en rojo:** el plan dice «cambia el semáforo a rojo». En el plan, rojo corresponde a Alerta y magenta a Crítico en la nave. Se mantiene esa correspondencia.
3. **`SIMULADO` es un origen y una etiqueta, no un valor de `EvidenceState` del contrato:** el enum del contrato tiene `VERIFICADO | TB | DEMO | NO_VERIFICADO`. El componente `EvidenceBadge` sí muestra `SIMULADO` cuando el origen es simulado.
4. **Versiones:** Vitest 3 y Vite 8 traían dos copias de Vite. Se pasó a Vitest 5.1.0 con Vite 8.3.8, un solo árbol.

**Pendientes de F0:**

- CODEOWNERS y job de CI de B: requieren repositorio con remoto. No se han creado.
- Revisar el arranque en navegador (`npm run dev`) para ver el banner visualmente.
- Contrato: pendiente de revisión de Dev A antes de congelar en I0.

**Estado:** F0 PARCIAL (cierra cuando haya repositorio para CODEOWNERS y CI).

### 2026-11-14 · E03 · F8 conocimiento con datos de demostración (TDD, Python)

**Entorno:** `.venv` en la raíz con Python 3.14, pydantic 2.14.3, pytest 9.2.0, ruff y mypy. `pyproject.toml` con `pythonpath = ["src"]`.

**RED:** `tests/knowledge/` con cuatro archivos (recomendación por alerta, contrato, catálogo y fachada) más `conftest.py`. Comando: `.venv/bin/python -m pytest tests/knowledge -q`. Resultado: error de colección `ModuleNotFoundError: spaceapp.modules.knowledge.adapters.outbound.demo_source`. Falla por módulo inexistente, como se esperaba.

**GREEN:** módulo `spaceapp.modules.knowledge` con `contracts.py` (payloads de `alert_raised` y `recommendation_ready`), `domain/model.py`, `ports/__init__.py`, `application/handle_alert_raised.py` (caso de uso idempotente), `adapters/outbound/{demo_source,memory}.py`, `facade.py` y el catálogo `data/knowledge/demo_catalog.json` con 8 reglas y 16 acciones. Resultado: `24 passed`.

**Garantías probadas (criterios de F8):**

| Criterio del plan | Prueba |
| --- | --- |
| `env-co2-1h` da una recomendación con al menos 2 acciones | `test_co2_alert_gets_at_least_two_actions` |
| Cita con documento, requisito y estado de evidencia | `test_co2_alert_gets_a_citation_with_document_requirement_and_evidence_state` (V2 6004, VERIFICADO) |
| Toda respuesta lleva la etiqueta DEMO | `test_recommendation_is_labelled_as_demo_and_says_it_is_not_from_nasa` y `test_every_rule_is_labelled_as_demo_source` |
| Evento duplicado no duplica | `test_same_event_delivered_twice_does_not_duplicate_the_recommendation` |
| Una recomendación por regla del catálogo | `test_every_rule_in_the_catalog_gets_a_recommendation` (8 casos parametrizados) |
| Contrato `RecommendationReady` según el plan | `test_recommendation_ready_has_exactly_the_payload_of_the_plan` |
| Sin modelo de lenguaje ni red | El caso de uso no recibe ningún compositor ni cliente HTTP |

**Calidad:**

- `ruff check src tests` → `All checks passed!` (se corrigió el orden de imports).
- `ruff format` → 1 archivo reformateado.
- `mypy` (modo estricto, `src`) → `Success: no issues found in 14 source files`. Se quitó un `type: ignore` que sobraba.

**Decisiones y desvíos:**

1. **`source_kind` no viaja en el evento.** El payload de `recommendation_ready` es el del plan (sección 4.1). Añadir un campo exige pedírselo antes a Dev A. Por eso la etiqueta DEMO va en el cuerpo de la recomendación («Esta recomendación usa un dato de demostración, no de NASA»). `source_kind` existe solo en el modelo interno. **Pendiente:** solicitud a Dev A para añadir `source_kind` al evento.
2. **Inbox local, no el de la plataforma.** La idempotencia usa un puerto `Inbox` con adaptador en memoria. En I1 lo sustituye el inbox real del outbox (dev A). Hasta entonces, la idempotencia vale solo dentro del proceso.
3. **Sin transacción con outbox todavía.** El plan pide guardar la recomendación y publicar el evento en la misma transacción. Sin base de datos ni outbox no se puede probar. El caso de uso ya está ordenado para que la sustitución sea directa.
4. **Id determinista:** `uuid5(alerta, regla)`. La misma alerta y la misma regla producen siempre el mismo id de recomendación, aunque lleguen con `event_id` distinto.
5. **Regla desconocida:** lanza `UnknownRuleError` antes de marcar el evento. Así un reintento del relay puede procesarlo después. Esto sigue la regla del plan de que el relay reintenta y mueve a `dead` tras 8 intentos.
6. **Citas de reglas de demostración:** `env-rh` y `env-t` citan el anclaje verificado V2 6013, pero su rango es DEMO, así que su `evidence_state` es `DEMO`. `env-tendencia` no tiene requisito de norma, y se cita como «Demostración (sin requisito)».

**Pendientes de F8:**

- Migración Alembic del esquema `knowledge` y persistencia real en PostgreSQL (depende de la plataforma de A).
- Integración con el bus real (I1, I4).

**Estado:** F8 HECHO en su parte de dominio y caso de uso, con pruebas. PARCIAL para lo que depende de A (persistencia, outbox, bus).

### 2026-11-14 · E04 · F6 y F7 (primer corte, TDD)

**Pasada RED → GREEN por componente.** Comando: `npx vitest run <carpeta>`. Cada componente se escribió con su prueba; los RED observados fueron `Failed to resolve import` por módulo inexistente.

| Módulo | RED observado | GREEN |
| --- | --- | --- |
| `features/cabin/AlertPanel.tsx` | Sí (módulo inexistente) | 7 pruebas |
| `features/cabin/CabinPanel.tsx` | Sí (módulo inexistente) | 4 pruebas |
| `data/ws/stream.ts` | **No observado.** Prueba y código se escribieron en el mismo lote y pasaron a la primera | 6 pruebas |
| `features/ship/ShipPlan.tsx` | Sí (módulo inexistente) | 9 pruebas (con casos de borde añadidos) |
| `features/ship/model.ts` | Sí (módulo inexistente) | 5 pruebas en `rules.test.ts` |

**Nota de método:** en `stream.ts` no hubo RED ejecutado antes de implementar. Esto incumple el ciclo que se fijó al inicio. La prueba sigue siendo válida como especificación, pero no hay evidencia de que haya fallado antes. Para próximas piezas se ejecutará el RED antes de escribir la implementación.

**Calidad de la pasada completa (final de E04):**

- `npx vitest run` → `Test Files 15 passed (15)`, `Tests 60 passed (60)`.
- `npx vitest run --coverage` → líneas 100 %, funciones 100 %, sentencias 100 %, ramas 92,53 %. Supera el umbral de 80 % en las cuatro métricas.
- `npx tsc --noEmit` → exit 0.

**Cambios que surgieron al llegar a la cobertura:**

1. **Se quitó `zoneStatus` de `features/ship/model.ts`:** no lo usaba nadie, así que era código muerto. Se prefirió quitarlo a probarlo.
2. **`src/main.tsx` quedó fuera de la cobertura:** solo monta la app y no tiene lógica. Lo verifican el build y, más adelante, la prueba en navegador.
3. **Casos de borde añadidos:** lista vacía del reproductor, `start()` repetido, regla sin requisito en el panel de alerta, tecla espacio en el plano, ticket resuelto no marcado en el plano, y zona crítica con trazo discontinuo (la forma acompaña al color).

**Decisiones de B en este corte:**

- **Reconocer:** `AlertPanel` solo emite `onAcknowledge`. La mutación GraphQL `acknowledgeAlert` llega cuando haya backend (I2 o después).
- **`aria-live="assertive"` solo para `CRITICO`:** el plan pide que la alerta crítica se anuncie con `aria-live`. Las demás quedan en `off` para no interrumpir.
- **El plano pinta el estado con texto y forma:** cada zona lleva su símbolo y su etiqueta (`Esclusa, Alerta`). Las zonas críticas tienen trazo discontinuo.
- **Cola WS sin React todavía:** `createStream` es lógica pura. Lo consumirá el hook `useWs` en la fase siguiente, cuando se conecte `/ws`.

**Lo que NO se hizo en F6 y F7 (y por qué):**

- **Gráficas uPlot y cuerpo humano SVG (F6.4, F6.5):** no tienen pruebas aún. Quedan para el siguiente corte.
- **Hook `useWs` y conexión a `/ws`:** depende de que A entregue el gateway (I2). Hasta entonces, la cola se prueba sola.
- **Formulario de reporte, catálogo de incidencias y modo demo (F7.5 a F7.7):** pendientes.
- **Gráficas por zona (F7.3):** pendientes.

**Estado:** F6 PARCIAL, F7 PARCIAL.

### Resumen de estado al cierre de la sesión

| Fase | Estado | Pruebas |
| --- | --- | --- |
| F0 | PARCIAL (faltan CODEOWNERS y CI, que necesitan repositorio) | 26 web |
| F8 | HECHO en dominio y caso de uso. PARCIAL en lo que depende de A | 24 Python |
| F6 | PARCIAL | incluido en las 60 web |
| F7 | PARCIAL | incluido en las 60 web |
| F12, F13, F14, F16 | PENDIENTE (no se empezaron en esta sesión) | — |
| F9, F10, F11 | PENDIENTE | — |

**Próximo paso sugerido:** el corte siguiente de F6 y F7 (gráficas, cuerpo humano, formulario de reporte) y después F13, el asistente de texto con `LlmGateway` nulo y tiempo límite de 8 s, que se puede probar sin Ollama.

### 2026-11-14 · E05 · F6 y F7, segundo corte (TDD)

**Pasada RED → GREEN por componente.** Cada prueba se ejecutó antes de implementar y falló por módulo inexistente, o por la aserción que describe el criterio, según el caso.

| Módulo | RED observado | GREEN |
| --- | --- | --- |
| `features/cabin/BodyMap.tsx` (F6.5) | Sí, módulo inexistente | 5 pruebas |
| `features/cabin/CabinPanel.tsx`, estado de espera (F6.7) | Sí, 1 prueba falló por aserción | 5 pruebas en el archivo |
| `features/charts/series.ts` y `LineChart.tsx` (F6.4) | Sí, módulo inexistente | 8 pruebas |
| `features/ship/ZoneCharts.tsx` (F7.3) | Sí, módulo inexistente | 5 pruebas, incluida la pausa congelada |
| `features/ship/ReportForm.tsx` (F7.5) | Sí, módulo inexistente | 5 pruebas. 2 fallaron por un nombre de tipo mal copiado en la prueba, y se corrigió la prueba |
| `features/ship/CatalogList.tsx` (F7.6) | Sí, módulo inexistente | 4 pruebas |
| `features/ship/DemoPanel.tsx` (F7.7) | Sí, módulo inexistente | 5 pruebas |

**Calidad al cierre de E05:**

- `npx vitest run` → `Test Files 22 passed (22)`, `Tests 93 passed (93)`.
- `npx vitest run --coverage` → líneas 99,43 %, funciones 98,76 %, sentencias 98,99 %, ramas 91,66 %. Supera el umbral de 80 % en las cuatro métricas.
- `npx tsc --noEmit` → exit 0.
- `npx vite build` → `✓ built in 177ms`, bundle 140,92 kB. No cambia porque `App` aún no importa los paneles nuevos.
- `npm run codegen` → `✔ Generate outputs`.

**Decisiones y desvíos de este corte:**

1. **Gráficas en SVG, no uPlot.** uPlot dibuja en canvas, y jsdom no lo puede probar. Con SVG la lógica es pura y se prueba. Cuando se pruebe en un navegador real, se puede cambiar el motor sin tocar `series.ts`.
2. **Ventana de 90 s y umbral etiquetado.** Las marcas (umbral, `ANOMALÍA`) llevan texto además de la forma, para no depender del color.
3. **Pausa congela las lecturas.** Al pausar, la gráfica muestra la última foto; al reanudar se pone al día con las lecturas que llegaron.
4. **Silueta del cuerpo pendiente.** El plan pide una silueta SVG con seis indicadores. Este corte tiene los seis indicadores como botones en lista; la silueta queda para después.
5. **Catálogo de 6 tipos, no de 61.** `incidentTypes.ts` es una muestra con la forma real del tipo (plan, sección 13.9). El catálogo completo es un dato versionado que llegará de A.
6. **Nombre de tipo corregido en la prueba.** El tipo «Olor a quemado» se llama «Olor a quemado o sobrecalentamiento» en el plan. La prueba usaba el nombre corto; se corrigió la prueba, no el fixture.
7. **Modo demo por perfil.** Visible solo en `dev1`, `dev2` y `jurado`. En cualquier otro perfil devuelve `null`.
8. **`zoneStatus` y estado vacío:** la función muerta de E04 sigue quitada. El estado de espera del panel de cabina se prueba en `CabinPanel.test.tsx`.

**Lo que sigue sin hacer en F6 y F7:**

- Hook `useWs` conectado a `/ws` y montar los paneles en `App`. Depende de A (I2).
- Mutaciones GraphQL reales (`acknowledgeAlert`, `reportIncident`, `resolveIncident`). Hoy los componentes solo emiten callbacks.
- Catálogo de 61 tipos y 12 categorías (dato de A).
- Estados de error del WebSocket y de GraphQL (6.7): pendientes con el hook.

**Estado:** F6 PARCIAL, F7 PARCIAL. Los componentes y su lógica están probados. Falta el cableado con el backend.

**Nota de método, repetida:** la pieza `stream.ts` de E04 no tuvo RED observado. No se volvió a repetir en E05.

### 2026-11-14 · E06 · Cableado de paneles en la app

**Qué:** la app deja de ser una pantalla vacía. Tiene dos vistas, Cabina y Nave, conectadas a un estado compartido con datos de demostración (sin backend todavía).

**Pasada RED → GREEN:**

| Módulo | RED observado | GREEN |
| --- | --- | --- |
| `app/scenario.ts`: estado puro (escenarios, zonas, tickets, alerta, series) | Sí, módulo inexistente | 10 pruebas |
| `ReportForm`: tipo preseleccionado desde el catálogo | Sí, 1 prueba falló por aserción | 6 pruebas en el archivo |
| `App.tsx`: integración de las vistas | Sí, pestaña «Nave» no encontrada | 7 pruebas |

**Flujos probados en `App.test.tsx`:** cambio de vista; provocar CO₂ alto en el laboratorio y ver la alerta con «Qué hacer» antes que el motivo; reconocer la alerta; «Normalizar todo» devuelve a normal; reportar desde el catálogo con el tipo precargado y el ticket aparece en el plano; seleccionar una zona abre sus gráficas.

**Calidad al cierre de E06:**

- `npx vitest run` → `Test Files 23 passed (23)`, `Tests 110 passed (110)`.
- `npx vitest run --coverage` → líneas 99,55 %, funciones 99,08 %, sentencias 98,81 %, ramas 91,89 %.
- `npx tsc --noEmit` → exit 0.
- `npx vite build` → bundle 159,45 kB (gzip 51,83 kB).

**Verificación en el navegador** (`vite` en 127.0.0.1:5173, detenido al terminar):

- Escritorio: el flujo completo funciona. El laboratorio pasa a «◆ Alerta» con su pin `INC-0001`, el semáforo global de la cabina pasa a Alerta, y el panel de alerta aparece.
- Problemas que se encontraron y se corrigieron:
  1. Las zonas del plano tenían 100 unidades de ancho y los nombres se pisaban. Se ensancharon a 130 y se redujo la fuente a 11 px.
  2. El pin del ticket salía en negro sobre fondo oscuro. Ahora usa el color de texto del tema.
  3. El panel de alerta estaba debajo del cuerpo humano. Se subió justo bajo el semáforo, porque el plan pide las acciones primero.
  4. A 375 px el plano era ilegible. Ahora tiene un ancho mínimo de 480 px y se desplaza dentro de su panel.
- A 375 px la cabina no tiene desplazamiento horizontal (`scrollWidth = 375`).

**Decisiones de B en E06:**

1. **Datos de demostración, no el backend.** El estado inicial es `initialState` y las consultas a GraphQL y `/ws` llegan en el hito I2. Por eso no hay hook de red; los componentes siguen recibiendo props.
2. **Tickets numerados por llegada:** `INC-0001`, `INC-0002`… Es un código de demostración. El backend asignará el suyo.
3. **Hora fija (`2026-11-14T10:00:00Z`)** en la app. Las pruebas no dependen del reloj.
4. **Escenarios de demo:** cada uno tiene una severidad y un título. Solo CO₂ alto cambia el dashboard de cabina y muestra la alerta con sus acciones; los demás abren un ticket y cambian la zona. Es una simplificación que se debe revisar cuando haya datos reales.
5. **Presión y nitrógeno marcados DEMO** en las series de zona: no tienen una fuente verificada en el plan.
6. **Estilos en `shared/layout.css`:** objetivos táctiles de 48 px, tarjetas de cabina en cuadrícula y plano con desplazamiento. Es presentación; no tiene pruebas automáticas, y se revisó a ojo en el navegador.

**Lo que no está hecho:**

- La tendencia de CO₂ en la vista de cabina (la gráfica existe, pero no está montada en cabina).
- Hook `useWs` y conexión a `/ws`; mutaciones GraphQL reales.
- Los estados de error del WebSocket y de GraphQL (6.7).
- Catálogo completo de 61 tipos (dato de Dev A).

**Estado:** F6 PARCIAL, F7 PARCIAL. La pantalla está cableada con datos de demostración y se verificó en escritorio y en teléfono.

### 2026-11-14 · E07 · F13 asistente de texto, y revisión del trabajo anterior

**Revisión al retomar (cambio de modelo en la sesión).** Antes de seguir se comprobó el estado real: Python 41 pruebas en verde, web 110 en verde y 2 suites en RED a propósito (las del asistente). Hallazgos y qué se hizo:

1. El caso de uso del asistente **no publicaba `assistant.answer_ready`** ni devolvía el `utterance_id`, y el plan lo pide. Se añadió con pruebas.
2. **`npm run lint` estaba roto:** el script existía pero ESLint no estaba instalado. Se instaló y no queda ningún hallazgo.
3. Faltaban el `.gitignore` y los READMEs cortos de `web`, `knowledge` y `assistant`, que exige la definición de hecho. Creados.
4. El mapa de fases de esta bitácora estaba desactualizado (decía «montar los paneles en `App`»). Actualizado.
5. **Corrección de E03:** el catálogo de demostración tiene **15 acciones**, no 16. Se verificó contando el JSON (`reglas 8, acciones 15, pasajes 3`).
6. La memoria del proyecto decía «sin código». Se actualizó y se añadieron dos memorias (avance real y forma de trabajo).

**F13 backend (Python)**

| Pieza | RED observado | GREEN |
| --- | --- | --- |
| Conocimiento: `DemoKnowledgeSource.search` | Sí, 4 pruebas fallaron | 4 pruebas |
| Conocimiento: fachada `KnowledgeQuery` | Sí, error de colección por importación | 1 prueba |
| Asistente: caso de uso `AskAssistant` y adaptadores (nulo, Ollama, memoria) | Sí, error de colección (módulo inexistente) | 10 + 2 pruebas |
| Asistente: `answer_ready` y `utterance_id` | Sí, error de colección (`ListPublisher` inexistente) | 3 pruebas |

En el caso de uso, 2 pruebas fallaron por un error **de mi prueba**: comparaba `result.text.lower()` con una cadena que tenía `mmHg` con H mayúscula. Se corrigió la prueba; el código devolvía el pasaje correcto.

**Criterios de aceptación de F13 y su evidencia**

| Criterio del plan | Prueba |
| --- | --- |
| «¿Por qué me duele la cabeza?» responde con el pasaje de TB-004 y su cita | `test_answers_a_headache_question_with_the_tb004_passage_and_its_citation` |
| Sin Ollama, o con más de 8 s, la respuesta llega igual con los pasajes | `test_falls_back_to_the_passages_when_the_model_exceeds_the_time_limit`, `..._when_the_model_fails`, `test_works_without_any_language_model` |
| Una pregunta sin pasaje no produce una respuesta inventada | `test_answers_no_information_without_calling_the_model_when_no_passage_is_relevant` |
| El asistente nunca cambia el estado de una alerta | Estructural: solo recibe un puerto de lectura (`ActiveAlerts.titles`). Además, la prueba de integración de `App` comprueba que tras preguntar la alerta sigue activa y el botón Reconocer sigue ahí |

**F13 web**

| Pieza | RED observado | GREEN |
| --- | --- | --- |
| `mockAnswer.ts` | Sí, módulo inexistente | 3 pruebas |
| `AssistantPanel.tsx` | Sí, módulo inexistente | 5 pruebas |
| `activeAlertTitles` en `app/scenario.ts` | Sí, 3 pruebas fallaron | 3 pruebas |
| Pestaña Asistente en `App` | Sí, 2 pruebas fallaron | 2 pruebas |

**Verificación en el navegador** (servidor de desarrollo, detenido al terminar): se provocó CO₂ alto en el laboratorio, se abrió el Asistente y se tocó la pregunta de ejemplo. La respuesta cita TB-004 y TB-003 con su estado de evidencia y nombra la alerta activa. De vuelta en la Cabina, el estado sigue en «◆ Alerta» y el botón Reconocer sigue ahí. A 375 px no hay desplazamiento horizontal. Problemas que se vieron y se corrigieron en `layout.css`: las líneas de la respuesta se colapsaban en un párrafo, los enlaces de las fuentes eran azul oscuro sobre fondo oscuro, y la etiqueta «Pregunta» quedaba pegada al campo.

**Calidad al cierre de E07**

- Web: `npm run lint` sin hallazgos. `npx tsc --noEmit` exit 0. `npx vitest run --coverage` → 25 archivos y 123 pruebas en verde; líneas 99,62 %, funciones 99,26 %, sentencias 98,67 %, ramas 90,47 %. `npx vite build` → 163,08 kB (gzip 53,02 kB). `npm run codegen` correcto.
- Python: `pytest tests` → 44 pruebas en verde. `ruff check` y `ruff format --check` limpios. `mypy` estricto sin problemas en 27 archivos.

**Decisiones y desvíos**

1. **TypeScript 7 → 6.0.3.** `typescript-eslint` solo soporta TypeScript hasta 6.0; usar `--legacy-peer-deps` habría dejado un árbol roto. Con 6.0.3, `tsc`, el build y las pruebas siguen pasando. Se pasó también `defineConfig` a `vitest/config` y se quitó una referencia de triple barra que ESLint marcó.
2. **Pasajes de demostración parafraseados del documento de contexto, no de los PDFs.** Los tres pasajes (TB-004, TB-003, TB-044) salen del resumen del contexto, que ya marcaba su estado (`TB` o `VERIFICADO`). **No se abrieron los PDFs.** Antes de presentarlos como citas literales hay que verificarlos contra la fuente (es parte de F12).
3. **Duplicación temporal en la web.** `mockAnswer.ts` y `data/mocks/passages.ts` replican la política y los pasajes del backend hasta que la interfaz consuma `askAssistant` (I2). Si el backend cambia, hay riesgo de que diverjan.
4. **Ollama no se ha probado contra un Ollama real.** El adaptador se prueba con una función de apertura falsa que devuelve NDJSON. No hay modelo elegido (decisión pendiente) ni se verificó el rendimiento sin GPU.
5. **El límite de 8 s deja de esperar, pero no cancela el hilo del modelo.** Si el modelo cuelga, el hilo sigue vivo hasta terminar. Mejora pendiente: poner el tiempo límite en la propia petición HTTP del adaptador. Las pruebas usan un límite de 0,05 s; el valor por defecto de 8 s no se ejecuta en ellas.
6. **Alerta activa:** se nombra como `título (severidad)` a partir de los tickets automáticos abiertos con valores aún fuera de rango.
7. **Citas fuera del modelo.** Las pone el caso de uso, así que el modelo no puede inventar una fuente.

**Lo que no está hecho en F13**

- Resolvers GraphQL (`askAssistant`, `confirmUtterance`, `conversation`): se registran en el esquema que compone Dev A.
- Tablas `conversation` y `utterance` en PostgreSQL y su migración; hoy las conversaciones viven en memoria.
- Adaptador de n8n (opcional) y adaptador real de `ActiveAlertsQuery`.
- Voz con Whisper y confirmación de lo transcrito (F14).

**Estado:** F13 PARCIAL. El flujo de texto funciona de punta a punta con datos de demostración y está probado.

### 2026-11-14 · E08 · Primer commit y ramas en GitHub

**Qué:** el trabajo de Dev B se subió a GitHub (`https://github.com/Julio-Cuellar/SpaceOverflow`).

- **Estado previo:** el directorio ya era un repositorio (alguien del equipo lo inicializó mientras se trabajaba) con un solo commit, `2d38c34 first commit`, que solo traía un `README.md`. `main` estaba sincronizada con `origin/main`. Hasta aquí esta bitácora decía que no era un repositorio; ya no es cierto.
- **Ramas creadas:** `dev-B`, `dev-A` y `testing`. **Git no permite espacios en nombres de rama**, así que `dev B` y `dev A` se llaman `dev-B` y `dev-A`.
- **Contenido:** `dev-B` tiene el commit `4babd3c` con 109 archivos (`web` 67, `src` 29, `tests` 8 y los de la raíz). `dev-A` y `testing` están en `2d38c34`, igual que `main`, sin cambios; quedan listas para que Dev A y las pruebas trabajen sobre ellas.
- **Antes de subir:** se revisó que no entrara ningún secreto ni archivo grande. El escaneo solo encontró falsos positivos (la palabra `token` de los tokens de diseño CSS). Ningún archivo supera 500 KB. `node_modules`, `.venv`, `dist`, `coverage` y las cachés están en el `.gitignore`.
- **Verificación en GitHub** (no solo en la terminal): `git ls-remote` y la API de GitHub muestran las tres ramas y `dev-B` en `4babd3c`, con 110 archivos (los 109 más el `README.md`).

**Para quien clone el repositorio:**

- Los tipos de `web/src/data/graphql/generated/` **no se versionan**. Se generan con `npm run codegen`. Ninguna prueba los importa, así que `npm install` y `npm test` bastan.
- El entorno de Python (`.venv`) tampoco se versiona: hay que crearlo e instalar `pydantic`, `pytest`, `ruff` y `mypy`. `pyproject.toml` lista las dependencias.

**Pendiente que ahora sí se puede hacer:** CODEOWNERS y el job de CI de F0 (antes bloqueados por no haber repositorio).

**Estado:** F0 sigue PARCIAL. Lo único que le falta es CODEOWNERS y CI.

### 2026-11-14 · E09 · F12 RAG sobre PDFs de NASA, y CI de GitHub Actions

**Límite de esta etapa:** todo el pipeline se construyó y se probó con PDFs **sintéticos**. **No se descargó ningún PDF real.** Descargar archivos requiere permiso explícito, y se pidió con nombre, origen y tamaño. Con peticiones `HEAD` (que no descargan) se comprobó que las 7 URLs responden `200 application/pdf` y suman **14,56 MB** (la norma Vol. 2 pesa 6,56 MB; el resto, entre 0,38 y 1,87 MB). Por eso **no hay ingesta real ni evaluación real todavía**.

**F12: RED → GREEN por pieza** (51 pruebas nuevas; Python pasa de 44 a 95)

| Pieza | RED observado | GREEN |
| --- | --- | --- |
| Manifiesto de documentos y licencias (`ingest/manifest.py`) | Sí, error de colección | 6 |
| Fragmentación por requisito (`ingest/chunking.py`) | Sí, error de colección | 8 |
| Lectura de PDF (`ingest/pdf.py`) | Sí, error de colección | 3 |
| Almacén, ingesta idempotente y comando (`ingest/store.py`, `pipeline.py`, `__main__.py`) | Sí, error de colección | 11 |
| Búsqueda RAG, glosario y respaldo a demo (`rag_source.py`, `domain/glossary.py`) | Sí, error de colección; 10 de 12 fallaron luego por el glosario ausente | 12 |
| Evaluación (`evaluate.py`) y preguntas | Sí, error de colección | 11 |

**Cómo se probó la lectura de PDF sin descargar nada:** `tests/knowledge/pdf_helpers.py` arma un PDF mínimo válido (con tabla de referencias cruzadas) y `pypdf` lo lee de vuelta.

**Un hueco que se encontró y se cerró bien:** al evaluar el glosario, una prueba falló porque la pregunta sobre capacidad aeróbica no recibía ninguna traducción. Al ver el detalle, otras pasaban solo por una traducción incidental (por ejemplo «astronauta» → `crew`, sin traducir «densidad ósea»). No se añadió lo mínimo para que pasara: se añadieron 13 entradas y la forma «vibrar» con los términos reales (`aerobic capacity`, `bone density`, `partial pressure`, `rate of change`, etc.).

**Garantías de F12 y su evidencia**

| Criterio del plan | Prueba |
| --- | --- |
| No se empaqueta ningún PDF sin licencia confirmada | `test_no_document_is_packageable_until_its_license_is_confirmed`, `test_rejects_a_manifest_that_packages_...` |
| Ingesta idempotente: reejecutarla no duplica | `test_running_it_twice_does_not_duplicate_anything` |
| Cada fragmento guarda documento, requisito, página y estado | `test_splits_a_page_at_each_requirement_reference` |
| Sin pasaje relevante no hay respuesta | `test_returns_nothing_when_no_passage_is_relevant` |
| La ingesta se ejecuta sin internet | El comando solo lee archivos locales y no descarga nada |
| Un PDF sin texto (escaneo) se avisa, no se ignora | `test_a_pdf_without_extractable_text_is_flagged_instead_of_ignored` |
| Cero respuestas sin fuente en la evaluación | `test_an_out_of_scope_question_must_not_get_any_passage` (la medición real espera a los PDFs) |

**Decisiones y limitaciones de F12**

1. **El idioma era un problema que el plan no previó.** Los documentos de NASA están en inglés y las preguntas en español; una búsqueda por términos no encontraría «headache» desde «dolor de cabeza». Solución provisoria: un **glosario español-inglés** (`data/knowledge/glossary_es_en.json`, 40 entradas) que expande la pregunta. Es una solución limitada: un término que no esté en el glosario no se encuentra. La solución de fondo es un modelo de embeddings multilingüe, que es la decisión pendiente n.º 5. **El glosario está pendiente de revisión del equipo.**
2. **El puntaje pondera por rareza** (`ln(1 + (N+1)/df)`) y exige un mínimo de 1,0: una palabra que está en casi todos los fragmentos no basta para devolver un pasaje.
3. **Posible inconsistencia de evidencia, para decidir.** El RAG toma el estado de evidencia del tipo de documento: todos los Technical Brief salen como `TB`. Pero el catálogo de demostración marca el pasaje de hipoxia de TB-003 como `VERIFICADO`, siguiendo el documento de contexto. No lo cambié porque esa clasificación es del equipo. Cuando se ingieran los PDFs reales, el mismo texto saldría como `TB`.
4. **Las preguntas de evaluación son hipótesis.** Los documentos esperados salen del documento de contexto, no de haber leído los PDFs. Hay que afinarlas tras la primera ingesta real. Son 16 dentro de alcance y 2 fuera.
5. **Los PDFs y su índice no se versionan** (`data/knowledge/pdfs/`, `data/knowledge/index/` en el `.gitignore`): la licencia de redistribución no está confirmada.
6. **No se extraen las tablas que vienen como imagen** (por ejemplo la Tabla 6.2-1). El plan pide transcribirlas a mano; no está hecho.
7. **El selector por perfil no está cableado.** Las clases (`RagKnowledgeSource`, `FallbackKnowledgeSource`) existen y están probadas, pero quien arma la aplicación es `main.py`, que es de Dev A.
8. **`pyproject.toml`:** se añadió `pypdf` y las dependencias de desarrollo pasaron a `[project.optional-dependencies]`, para que el CI instale con `pip install -e ".[dev]"`.

**CI de GitHub Actions** (`.github/workflows/ci.yml`) y **CODEOWNERS** (`.github/CODEOWNERS`)

- **Se ejecuta** en cada pull request y en cada push a `main`, `dev-A`, `dev-B` y `testing`. Permisos de solo lectura; un push nuevo cancela la ejecución anterior de esa rama.
- **Job `web`:** `npm ci`, lint, tipos, cobertura (falla por debajo del 80 %), build y codegen.
- **Job `python`** en 3.12 y 3.14: `pip install -e ".[dev]"`, `ruff check`, `ruff format --check`, `mypy` y `pytest`.
- **Verificación en una copia limpia** (clon de `dev-B` en una carpeta temporal, sin mi `node_modules` ni mi `.venv`): los 6 pasos de `web` pasan (cobertura de líneas 99,62 %) y los 5 pasos de `python` pasan en 3.14 (95 pruebas).
- **Lo que NO se pudo verificar:** Python 3.12 no está instalado en este equipo. Solo se comprobó que los 52 archivos parsean con la gramática de 3.12 y que `mypy --python-version 3.12` no da problemas. La ejecución real en 3.12, y el CI en un runner de GitHub, ocurren por primera vez al subir esta rama. Si 3.12 falla, se corrige.
- **Hallazgo durante la verificación:** hasta ahora el build se había comprobado con `npx vite build`, no con el script real (`tsc -b && vite build`). Se ejecutó el script real y pasa.
- **CODEOWNERS** solo cubre las carpetas de Dev B. Falta el usuario de GitHub de Dev A (se dejó anotado como pendiente en el propio archivo).

**Estado:** F12 PARCIAL (pipeline probado; falta la ingesta y la evaluación reales). CI y CODEOWNERS creados; pendiente su primera ejecución en GitHub.

### 2026-11-14 · E10 · F12 con los PDFs reales: descarga, ingesta y evaluación

**Permiso:** el usuario autorizó con nombre, origen y tamaño la descarga de los 7 PDFs (14,56 MB). Se descargaron a `data/knowledge/pdfs/` (ignorada por git) y se comprobó que los 7 empiezan con `%PDF-`. No se descargó nada más.

**Ingesta real:** 2 087 fragmentos (Vol. 2: 1 456; Vol. 1: 291; TB-002: 116; TB-003: 76; TB-004: 56; TB-044: 52; botiquín: 40). Solo 665 llevan referencia de requisito: el resto es texto de tablas, listas y secciones sin `[V# ####]` propio.

**Defectos que solo aparecieron con los PDFs reales** (cada uno se reprodujo con una prueba en RED antes de corregirlo)

| Defecto | Causa | Corrección |
| --- | --- | --- |
| Una cita dentro de una frase partía el fragmento | `[V2 6004]` precedido de una letra minúscula, «(» o «,» es una cita en línea, no el comienzo de un requisito | `_starts_a_requirement` |
| Fragmentos viejos quedaban en el índice tras cambiar las reglas de corte | Los ids cambian al recortar distinto; la ingesta solo añade | Opción `--rebuild` (reconstruye en memoria y reemplaza de forma atómica; si no se indexó nada, conserva el índice anterior) |
| Una tabla que lista «headache» entre decenas de términos ganaba a un pasaje enfocado | El puntaje contaba coincidencias sin normalizar por longitud | BM25 (K1 1,5; B 0,75) |
| «dura» → `lasts`, pero el texto dice `last` | Faltaba normalizar plurales y terceras personas | `stem` |
| Con 500 caracteres de extracto la cifra quedaba fuera en la mitad de los casos | Recorte al comienzo del fragmento | El extracto es el fragmento completo (≤ 1 200) |
| «Who won the last football world cup?» recibía una respuesta | Coincidía solo en «world», dentro de una lista de siglas | Se exigen al menos 2 términos coincidentes (con 1 término de pregunta, 1) |
| Títulos y entradas de índice salían como pasajes | Fragmentos de 2 o 3 palabras | Se descartan los de menos de 6 palabras de contenido |
| Una referencia cruzada tras un dígito («…Volume 1 [V1 4030] Título)») partía V1 4033 y la cifra de 1,3 mSv/día se citaba como V1 4030 | La regla de «número de página» la tomaba por requisito | Dentro de un paréntesis sin cerrar es una cita (prueba en RED observada; 120 pruebas pasan) |
| El comando de evaluación fallaba con un traceback si faltaba un archivo | — | Mensaje claro y código de salida 2 |

**Cómo se evaluó (y por qué se cambió)**

- Mis preguntas de la entrada E09 eran hipótesis basadas en el documento de contexto (esperaban un documento concreto). Se reemplazaron por **anclas de contenido**: texto que debe aparecer en el pasaje devuelto, verificado a mano en el texto crudo de los PDFs.
- Se añadió un conjunto **de validación retenido** (`eval_questions_validation.json`, 9 + 1 fuera de alcance). **No se ajusta el código mirando ese conjunto**: sirve para medir si lo corregido generaliza.
- Se añadió un conjunto **en inglés** (`eval_questions_en.json`, 25 + 3 fuera de alcance), de diagnóstico: separa el fallo de traducción del fallo de búsqueda.
- La métrica es **estricta**: acierta solo si en los 3 primeros hay un pasaje con las anclas (y, si se pide, el documento).

**Resultados medidos** (k = 3, índice de 2 087 fragmentos)

| Conjunto | Aciertos | Fuera de alcance respondidas |
| --- | --- | --- |
| Principal, español (16 + 2) | 9 de 16 (56 %) | 0 de 2 |
| Validación retenido, español (9 + 1) | **1 de 9 (11 %)** | 0 de 1 |
| Diagnóstico, inglés (25 + 3) | 13 de 25 (52 %) | 0 de 3 |

El umbral del plan (80 %) **no se cumple** y el comando de evaluación sale con código 1. No se bajó el umbral ni se ajustaron las preguntas para que pasara.

**Lectura honesta de los números**

1. **Cero respuestas sin fuente:** ninguna pregunta fuera de alcance recibió pasaje (0 de 6). Es el criterio que más importa para no inventar protocolos, y se cumple.
2. **La recuperación es débil.** El conjunto en inglés también falla en la mitad: el problema no es solo el idioma. Es búsqueda léxica sobre un documento de ~300 páginas con vocabulario técnico: una paráfrasis («energía diaria» frente a *energy requirements*) o una cifra en una tabla no se encuentran por coincidencia de palabras.
3. **La brecha entre 56 % y 11 %** es el sobreajuste esperado: el glosario (40 entradas) se afinó mirando el conjunto principal. El conjunto retenido muestra el rendimiento sin ese ajuste, y ese es el número que hay que creer.
4. **Fallos concretos** (posición del pasaje correcto en el ranking, en una medición intermedia): dolor de cabeza, puesto 21; síntomas del CO₂, 27; presión mínima de cabina, 19; botiquín, 26.

**Verificado contra el texto fuente** (consultando los fragmentos indexados)

- Ruido de sueño: `[V2 6079]` y NC-40, para misiones de más de 30 días (Vol. 2, p. 98). Coincide con el documento de contexto. La fila de la tabla resumen (p. 94) cita «V2 6077; V2 6078; V2 6080; V2 6083» porque agrupa otros límites: no es una discrepancia.
- Las cifras clave del contexto (1,3 mSv/día, 600 mSv de carrera, 250 mSv por evento solar, 80 % de capacidad aeróbica, 95 % de hueso, 30 % de diluyente, 95 dBA en alarmas) aparecen en el texto indexado con los números de requisito que el contexto indica en el texto cercano. Los fragmentos largos rara vez llevan el requisito propio en su campo `requirement_ref` (la mayoría de las cifras están en fragmentos sin él), así que **la cita sale con documento y página, no siempre con número de requisito.**
- **Limitación abierta, sin corregir:** si el título de la sección que precede a `[V1 4033]` termina en minúscula («…Galactic Cosmic Radiation [V1 4033]»), la regla lo toma por cita y el requisito queda sin `requirement_ref` (Vol. 1, p. 44). Antes de la corrección de paréntesis esa cifra se citaba con el número equivocado (V1 4030); ahora se cita sin número, que es más honesto, pero incompleto.

**Decisiones que quedan para el equipo (no las tomé)**

1. **Modelo de embeddings multilingüe** (decisión pendiente n.º 5). Es la solución de fondo a la recuperación débil. Cuesta: descargar un modelo (requiere permiso explícito), dependencias pesadas (PyTorch u ONNX), y empaquetarlo sin conexión en Docker. Alternativa barata y parcial: ampliar el glosario revisándolo con el equipo, sabiendo que no generaliza.
2. **Estado de evidencia.** El RAG da `TB` a todo Technical Brief; el catálogo de demostración marca TB-003 como `VERIFICADO`. Hay que decidir cuál vale.
3. **Revisión del glosario** (40 entradas, mías, sin revisar por nadie del equipo).
4. **Licencia de los PDFs:** sigue `no_verificada`; por eso nada se empaqueta ni se versiona.

**Qué no cambió:** el asistente sigue sin decidir alertas y solo responde con pasajes citados; ante la duda no responde («sin información»). La debilidad de recuperación se traduce en que **no responde más veces de las debidas**, no en que invente.

**Lo que sigue sin hacerse en F12:** buscador de pasajes en la web (12.6), tablas como imagen sin transcribir, selección de fuente por perfil (depende de `main.py`, de Dev A).

**Estado:** F12 PARCIAL. Ingesta y evaluación reales hechas; el umbral de recuperación del plan (80 %) no se cumple.

**Verificación al cierre:** 120 pruebas de Python pasan; `ruff check`, `ruff format --check` y `mypy` estrictos limpios.
