# Tareas de Dev B · interfaz, conocimiento y RAG

> NASA Space Apps 2026 · monitor de salud para astronautas
> Documento de trabajo para **Dev B**. Deriva de [`plan-arquitectura.md`](plan-arquitectura.md) (sobre todo las secciones 5, 8, 10, 13 y 16) y de [`spaceapps-health-monitor-context.md`](spaceapps-health-monitor-context.md).
> Artefacto interactivo con el reparto, los diagramas y el prototipo de la interfaz: https://claude.ai/artifact/LMrTxLRghTr9h3v2Q79am8
> Estado: **propuesta, pendiente de confirmación del plan**. Las horas son de trabajo por persona, no de reloj.

---

## 0. Resumen

| | |
| --- | --- |
| **Rol** | Dueño de toda la interfaz (SPA) y de los módulos `knowledge` y `assistant`. **Todo el RAG es suyo.** |
| **Horas** | 34 h en total. 18,5 h en el corte P0 y 15,5 h en P1 y P2 |
| **RAG** | 15 h repartidas en cinco fases: F8, F12, F13, F14 y F16 |
| **Fases** | F0 (conjunta), F6, F7, F8, F12, F9 (conjunta), F13, F14, F10 (interfaz), F11 (interfaz) y F16 |
| **Lenguajes** | TypeScript (React) en `web/`. Python (FastAPI) en los módulos `knowledge` y `assistant` |
| **Compañero** | Dev A: plataforma, telemetría, monitoreo, nave e incidencias, tripulación, misiones, enlace con Tierra y gateway GraphQL y WebSocket |
| **Regla de oro** | B no depende de A hasta el hito I2. Hasta entonces trabaja sobre mocks generados del contrato |

### Línea de tiempo de Dev B

| Horas | Fase | Nombre | Prioridad | Esfuerzo | RAG |
| --- | --- | --- | --- | --- | --- |
| 0 a 1 | F0 | Cimientos (conjunta con A) | P0 | 1 h | |
| 1 a 7 | F6 | Interfaz de cabina | P0 | 6 h | |
| 7 a 14 | F7 | Panel de la nave | P0 | 7 h | |
| 14 a 17 | F8 | Conocimiento con datos de demostración | P0 | 3 h | RAG |
| 17 a 21 | F12 | RAG sobre PDFs de NASA | P1 | 4 h | RAG |
| 21 a 22,5 | F9 | Entrega para el jurado (conjunta) | P0 | 1,5 h | |
| 22,5 a 25,5 | F13 | Asistente: texto y Ollama | P1 | 3 h | RAG |
| 25,5 a 28,5 | F14 | Voz con Whisper | P1 | 3 h | RAG |
| 28,5 a 30 | F10 | Tareas (interfaz) | P1 | 1,5 h | |
| 30 a 32 | F11 | Panel del centro de control (interfaz) | P1 | 2 h | |
| 32 a 34 | F16 | Alexa como respaldo | P2 | 2 h | RAG |

F12 está marcada P1 en el plan, pero **cabe antes de la entrega** sin retrasar el hito I6. Subirla a P0 es una decisión pendiente (sección 11).

### Hitos en los que B interviene

| Hito | Hora | Qué hace B |
| --- | --- | --- |
| I0 · Contratos congelados | 1 | Revisa y acepta esquema GraphQL, mensajes WS y OpenAPI. Deja listos mocks y generación de tipos |
| I1 · Outbox real | 4 | Cambia el bus en memoria por el outbox real en los handlers de Conocimiento (cuando exista F8) |
| I2 · Lecturas y simulador en vivo | 11 | Conecta los ticks WebSocket al panel de cabina |
| I3 · Incidencias en vivo | 16 | Conecta el panel de la nave a `ship`, `incidents` y `incident.*` |
| I4 · Alerta con recomendación citada | 17 | Conocimiento recibe `alert_raised` real y publica `recommendation_ready`. Se ve en el panel de alerta |
| I5 · GraphQL y WebSocket completos | 20 | Retira todos los mocks. Primera prueba de extremo a extremo |
| I6 · Entrega para el jurado | 22,5 | Prueba la imagen sin internet en otra computadora |
| I7 · P1 completo | 32 | Plan desde Tierra de punta a punta, del lado de la interfaz |

---

## 1. Alcance

### 1.1 Qué es de B

- **SPA completa** en `web/` (React, Vite y TypeScript): panel de cabina, panel de la nave, tareas del día, asistente, enlace y privacidad, y panel del centro de control (`/ground`).
- **Módulo `knowledge`:** documentos, fragmentos con cita, catálogo de acciones, recomendaciones, ingesta y búsqueda.
- **Módulo `assistant`:** conversaciones por texto y voz, respuestas con cita y en streaming.
- **Adaptadores locales:** Ollama (redacción), Whisper (voz) y Alexa (respaldo, solo demo).
- **Resolvers GraphQL** de Conocimiento y Asistente, y las rutas REST de audio (`R2`) y de Alexa (`R3`).
- **Su parte de la imagen de Docker:** servir la SPA y aislar las dependencias pesadas del RAG.

### 1.2 Qué no es de B

- Reglas de monitoreo, cálculo de PIO₂, ventanas y detección de anomalías: son del módulo `monitoring` (A). **La interfaz muestra lo que calcula el backend y no lo recalcula.**
- Outbox, relay, inbox y `UnitOfWork`: son de la plataforma (A).
- Simulador, ingesta de lecturas y escenarios: telemetría (A).
- Tablas `habitat`, `zone`, `incident`, `task`, `task_template` y las de enlace: son de A. B las consume por GraphQL.
- El gateway `/ws` y la composición del esquema GraphQL: A. B registra sus resolvers y consume los mensajes.

### 1.3 Reglas del proyecto que B debe respetar siempre

1. **El modelo de lenguaje nunca decide una alerta.** B solo explica, y nunca bloquea una alerta esperando a Ollama.
2. **Toda cifra sin fuente verificada se rotula `DEMO`.** Los datos del cuerpo llevan además la marca «simulado».
3. **Banner permanente:** «Prototipo de apoyo a la decisión. No es un dispositivo médico».
4. **El color nunca va solo.** Cada estado lleva forma, icono y texto: ● Normal, ▲ Atención, ■ Crítico.
5. **Nunca se inventa un protocolo médico.** Si no hay pasaje que respalde la respuesta: «No tengo esa información en las fuentes cargadas».
6. **Nada se ejecuta por voz sin confirmar** lo transcrito, y siempre hay entrada por texto.
7. **Una emergencia nunca depende de que el astronauta hable.** La alerta sale de los sensores.
8. Textos de interfaz y documentación en **español**.
9. **Alexa no es autónoma**: se dice así en la interfaz y en la presentación.

---

## 2. Cómo trabaja B sin esperar a A

### 2.1 Contract-first

En la Fase 0 se congelan, entre los dos:

- **Eventos** en `contracts.py` (modelos Pydantic versionados).
- **Esquema GraphQL** (`schema.graphql`) con tipos, enumeraciones y uniones de resultado.
- **Mensajes WebSocket** (`ws-messages.schema.json`).
- **OpenAPI** de las rutas REST.

Un cambio de contrato exige revisión del otro desarrollador. Cualquier cambio rompe el build de B de inmediato por la generación de tipos.

### 2.2 Mocks para la interfaz

- **GraphQL:** servidor simulado con MSW, generado del esquema, con fixtures por escenario (normal, CO₂ alto, fuga de presión, humedad, fallo de O₂).
- **WebSocket:** reproductor de mensajes grabados (`web/src/data/mocks/ws/*.json`). Las grabaciones salen de los escenarios del artefacto: ticks a 1 Hz, `alert.raised`, `zone.status`, `incident.opened`, etc.
- **Se retiran** en los hitos I2, I3 y I5, a medida que A entrega lo real.

### 2.3 Bus en memoria para Conocimiento

A entrega en F0 un `InMemoryEventBus` con la misma interfaz `EventBus` que el outbox. B desarrolla el handler de `alert_raised` sobre él y lo cambia por el real en I1. Los handlers deben ser **idempotentes** desde el principio (inbox por `(consumer, event_id)`).

### 2.4 Estructura de carpetas

```text
web/
  src/
    app/                    # rutas, proveedores, layout
    shared/
      ui/                   # Badge de evidencia, SevPill, Gauge, Card, Banner
      lib/                  # severity.ts, evidence.ts, format.ts
      tokens.css            # colores semánticos, tema claro y oscuro
    features/
      cabin/                # panel de cabina, cuerpo humano, panel de alerta
      ship/                 # plano, tickets, gráficas por zona, catálogo
      tasks/                # tareas del día, nueva tarea
      assistant/            # chat, voz, citas, buscador de pasajes
      link/                 # enlace y privacidad
      ground/               # panel del centro de control
    data/
      graphql/              # documentos .graphql y tipos generados
      ws/                   # useWs(topics), cola, resume
      mocks/                # handlers MSW y grabaciones WS
  codegen.ts, vite.config.ts, vitest.config.ts

src/spaceapp/modules/knowledge/
  domain/  application/  ports/
  adapters/inbound/       # events.py (alert_raised), graphql.py
  adapters/outbound/      # sql.py, demo_source.py, rag_source.py, ollama.py
  contracts.py  facade.py
src/spaceapp/modules/assistant/
  domain/  application/  ports/
  adapters/inbound/       # rest.py (audio), alexa.py, graphql.py
  adapters/outbound/      # sql.py, whisper.py, ollama.py
  contracts.py  facade.py
migrations/knowledge/  migrations/assistant/
data/knowledge/         # fragmentos de demostración y manifiesto de documentos
```

### 2.5 Convenciones

- **Ramas:** `b/<fase>-<tema>`, de menos de 2 h. Se integra a `main` con CI en verde.
- **CI de B:** `eslint`, `tsc --noEmit`, `vitest`, generación de tipos desde el esquema, `ruff`, `mypy`, `import-linter` y `pytest` de sus módulos.
- **`CODEOWNERS`:** `web/`, `modules/knowledge/`, `modules/assistant/`, `migrations/knowledge/` y `migrations/assistant/` son de B.
- **Límites entre módulos:** B solo importa de otro módulo su `contracts` y su `facade`. Nunca `domain`, `adapters` ni modelos SQL.
- **Un esquema de PostgreSQL por módulo** y sin claves foráneas hacia otros módulos (solo referencias blandas por id).

---

## 3. Fases en detalle

Cada fase indica objetivo, horas, dependencias, tareas con su estimación, criterios de aceptación y pruebas. Las casillas sirven para seguimiento.

### F0 · Cimientos (conjunta con A) · 1 h · P0

**Objetivo:** dejar el repositorio, los contratos y las herramientas listos para trabajar en paralelo. A lleva el repositorio y el `InMemoryEventBus`. B lleva `web/` y los mocks.

**Depende de:** nada.

**Tareas de B**

- [ ] **0.1 Proyecto `web/` (0,25 h):** Vite, React 18, TypeScript estricto, ESLint, Vitest y alias de rutas.
- [ ] **0.2 Cliente GraphQL y generación de tipos (0,25 h):** urql, `graphql-codegen` leyendo `schema.graphql`. El comando `npm run codegen` falla si el contrato cambia sin actualizar los documentos.
- [ ] **0.3 Mocks (0,25 h):** MSW con un handler de `dashboard` y un reproductor de mensajes WS de ejemplo.
- [ ] **0.4 Contratos y revisión (0,25 h):** revisar con A el esquema, los eventos y los mensajes WS. Registrar `CODEOWNERS` y el job de CI de B.

**Criterios de aceptación**

- `npm run dev` abre una pantalla vacía con el banner permanente.
- `npm run codegen` genera tipos sin errores.
- El mock devuelve un `dashboard` de ejemplo y el reproductor emite un `telemetry.tick`.
- El esquema, los eventos y los mensajes WS quedan marcados como **congelados (I0)**.

---

### F6 · Interfaz de cabina · 6 h · P0

**Objetivo:** que el astronauta entienda su estado de un vistazo y pueda actuar ante una alerta.

**Depende de:** F0. **Mock:** servidor GraphQL simulado y mensajes WS grabados.

**Contratos que consume**

| Canal | Operación o mensaje |
| --- | --- |
| GraphQL | `dashboard`, `readings`, `alerts`, `alert`, `rules`, `crewMember`, `acknowledgeAlert` |
| WebSocket | `telemetry.tick`, `alert.raised · alert.updated · alert.resolved`, `recommendation.ready · recommendation.enriched`, `scenario.changed`, `groundlink.state`, `subscribe`, `resume`, `ping` |
| REST | `POST /api/v1/sim/scenarios/{key}:start · :stop` (modo demo) |

**Tareas**

- [ ] **6.1 Shell, tema y componentes base (0,5 h)**
  - Diseño con tokens semánticos (semáforo, evidencia, superficie) en claro y oscuro. Oscuro por defecto para cabina.
  - Componentes: `EvidenceBadge` (`VERIFICADO`, `TB`, `DEMO`, `SIMULADO`), `SevPill` con icono (● ▲ ■), `Card`, `Gauge`, `Banner`.
  - Banner permanente «Prototipo de apoyo a la decisión. No es un dispositivo médico» y marca «Datos simulados».
  - Objetivos táctiles de 48 px o más, contraste AA y foco visible.
- [ ] **6.2 Capa de datos y tiempo real (0,75 h)**
  - Hook `useWs(topics)`: conexión única a `/ws`, `subscribe`, cola por topic y deduplicación por `seq`.
  - **Resume:** guarda el último `seq` y envía `resume { after_outbox_id }` al reconectar.
  - Barra «Reconectando… mostrando el último dato de hace N s».
  - Coalescencia de `telemetry.tick`. **Las alertas nunca se descartan.**
- [ ] **6.3 Panel de cabina (1,25 h)**
  - Semáforo global con la peor severidad.
  - Tarjetas: oxígeno (PIO₂ con gauge y bandas), CO₂ (ppCO₂), presión y velocidad de cambio, radiación y chip de enlace con Tierra.
  - Cada valor muestra su estado de evidencia. Las bandas amarillas, que son propuesta del equipo, llevan `DEMO`.
  - **No se recalcula PIO₂ en el cliente:** se muestra el valor del `dashboard`.
- [ ] **6.4 Gráficas dinámicas (0,75 h)**
  - Series con uPlot desde `readings` y actualización en vivo con `telemetry.tick`.
  - Ventana configurable, bandas de severidad dibujadas y marca del umbral.
  - Gráficas legibles en modo claro y oscuro.
- [ ] **6.5 Cuerpo humano (0,75 h)**
  - Silueta SVG con seis indicadores: cabeza (ánimo y cefalea), pulmones (SpO₂), corazón, sangre y órganos (radiación), temperatura y huesos y músculo.
  - Cada indicador usa el semáforo con número e icono. Al tocarlo: valor, peligro del programa de investigación humana de NASA con el que se relaciona y estado de evidencia.
  - Los valores del cuerpo llevan `DEMO` y «simulado».
- [ ] **6.6 Panel de alerta (1,25 h)**
  - **Acciones primero**, después el motivo. Orden: qué hacer, por qué (regla, valor medido, documento, requisito y estado), causa probable (aire o cuerpo), cuándo escalar.
  - Botón **Reconocer** (`acknowledgeAlert`) con estado optimista y manejo del error tipado.
  - Muestra primero `recommendation.ready` (plantilla con citas) y después `recommendation.enriched` (texto del modelo) **sin saltos de diseño**.
  - Alerta crítica: borde, sonido y vibración opcionales, y `aria-live`.
- [ ] **6.7 Estados vacíos y de error (0,75 h)**
  - Sin datos: «Esperando lecturas del simulador» con esqueleto.
  - WebSocket caído, error de GraphQL, sin recomendación todavía y modelo ausente.
  - Selector de entorno (nave, estación, rover o base) y pantalla de escenarios para la demo.

**Criterios de aceptación**

- Con los mocks, el escenario de CO₂ alto cambia el semáforo a rojo, muestra la alerta con acciones y fuente, y permite reconocerla.
- Todo estado tiene forma, icono y texto, no solo color.
- Se ve el banner de «no es dispositivo médico» en todas las pantallas.
- Cortar y restablecer el WebSocket reanuda sin perder alertas ni duplicarlas.
- Lighthouse de accesibilidad de 90 o más y navegación completa por teclado.

**Pruebas**

- Vitest + Testing Library: `SevPill`, `EvidenceBadge`, gauge con bandas, `useWs` (resume y duplicados).
- Playwright contra mocks: escenario de CO₂, reconocer alerta, caída del WebSocket.

---

### F7 · Panel de la nave · 7 h · P0

**Objetivo:** mostrar el plano de la nave con sus zonas, los tickets de incidencia y las gráficas de gases por zona, medidos de forma continua.

**Depende de:** F0. **Mock:** igual que F6, más fixtures de `ship`, `incidents` e `incidentTypes`. En I3 (hora 16) pasa a lo real.

**Contratos que consume**

| Canal | Operación o mensaje |
| --- | --- |
| GraphQL | `ship`, `incidents`, `incident`, `zoneReadings`, `incidentTypes`, `reportIncident`, `acknowledgeIncident`, `resolveIncident` |
| WebSocket | `incident.opened · incident.updated · incident.resolved`, `zone.status`, `telemetry.tick` (por zona), `task.assigned` |
| REST | `POST /api/v1/sim/scenarios/{key}:start · :stop` con `zone_id` (modo demo) |

**Tareas**

- [ ] **7.1 Plano SVG (1,5 h)**
  - Se dibuja desde `ship` usando `zone.layout` (JSON: posición y tamaño). **Nada de coordenadas fijas en el código:** cambiar de nave a base lunar es cambiar datos.
  - Cada zona tiene color por estado (verde, ámbar, rojo, magenta), icono de severidad y trazado rayado para el crítico.
  - Pin con el identificador del ticket (`INC-0001`) y `+n` si hay más.
  - Selección por clic y por teclado. Lectura rápida de CO₂ y O₂ dentro de cada zona.
- [ ] **7.2 Tiempo real (0,75 h)**
  - Suscripción a `zone.status` e `incident.*`. Actualiza el plano y la lista sin recargar.
  - `telemetry.tick` por zona alimenta las gráficas y la lectura rápida.
- [ ] **7.3 Gráficas por zona (1,5 h)**
  - Seis métricas: O₂ (PIO₂), CO₂ (ppCO₂), N₂, humedad, temperatura y presión.
  - Ventana de 90 s en vivo, con bandas de severidad y marca **ANOMALÍA** cuando el backend la reporta. Histórico con `zoneReadings`.
  - Valor actual con color, icono de estado y etiqueta de evidencia (las bandas de humedad y temperatura son `DEMO`).
  - Indicador «en vivo» y botón de pausa.
- [ ] **7.4 Tickets (1,25 h)**
  - Tarjeta con identificador, severidad, estado, título, **ubicación** (zona y cubierta), origen (alerta automática o reporte manual), **descripción**, historial y tareas.
  - Acciones: reconocer y resolver. En tickets automáticos, **resolver queda deshabilitado mientras los valores sigan fuera de rango**, con la explicación a la vista.
  - Aviso «Valores normales: puede cerrarse» cuando llega `alert_resolved`.
  - Orden por severidad y antigüedad. Los resueltos se atenúan.
- [ ] **7.5 Formulario de reporte (1 h)**
  - Categoría → tipo → zona y severidad por defecto, desde `incidentTypes`. Título opcional (si queda vacío se usa el tipo) y descripción.
  - Envía `reportIncident`. Manejo de `IncidentError` tipado.
- [ ] **7.6 Catálogo de tipos (0,5 h)**
  - Lista de los 61 tipos en 12 categorías, filtrable. Cada fila muestra detección (`AUTO` o `MANUAL`), severidad, evidencia y zonas típicas.
  - Botón «Reportar» que rellena el formulario.
- [ ] **7.7 Modo demo (0,5 h)**
  - Botones para provocar escenarios por zona (fuga de presión, CO₂ alto, humedad, fallo de O₂, calor) y «Normalizar todo».
  - Solo visible en perfiles de desarrollo y jurado.

**Criterios de aceptación**

- Con los mocks, un escenario por zona pinta la zona, abre un ticket con descripción, severidad y ubicación, y aparece en la lista y como pin en el plano.
- Seleccionar una zona o un ticket muestra sus gráficas.
- El plano se dibuja solo con datos: cambiar el JSON de `zone.layout` cambia el plano.
- La interfaz funciona con 360 px de ancho: el plano se desplaza dentro de su panel.
- Los seis indicadores gráficos tienen forma, icono y texto.

**Pruebas**

- Vitest: render del plano desde datos, orden de tickets y regla del botón «Resolver».
- Playwright contra mocks: provocar escenario → ticket → reconocer → normalizar → resolver.
- Prueba visual de claro y oscuro.

---

### F8 · Conocimiento con datos de demostración · 3 h · P0 · RAG

**Objetivo:** que cada alerta tenga una recomendación determinista con cita, sin depender de ningún modelo.

**Depende de:** F0. **Mock:** bus en memoria con eventos `alert_raised` de ejemplo y una fachada `RuleQuery` falsa.

**Contratos**

| Dirección | Contrato |
| --- | --- |
| Consume | Evento `monitoring.alert_raised` (payload: `alert_id`, `zone_id`, `rule_key`, `severity`, `evidence`, `cause_hint`). Fachada `RuleQuery` de Monitoreo (regla y `action_key`) |
| Publica | `knowledge.recommendation_ready` (`alert_id`, `recommendation_id`, `action_keys[]`, `citations[]`) |
| Expone | Fachadas `KnowledgeQuery` y `ActionCatalogQuery`. GraphQL `knowledgeSearch(query, k)` |

**Tareas**

- [ ] **8.1 Esqueleto hexagonal (0,5 h)**
  - Puertos: `KnowledgeSource`, `TextComposer`, `ChunkRepository`. Adaptadores: `demo_source`, `template_composer`, `sql`.
  - `contracts.py` con `RecommendationReady` y `Citation`. `facade.py` de solo lectura.
- [ ] **8.2 Esquema y migración (0,5 h)**
  - Esquema `knowledge` con `document`, `chunk`, `action`, `recommendation` y `recommendation_action` (ver sección 4.2). Migración Alembic propia en `migrations/knowledge/`.
- [ ] **8.3 Adaptador de demostración (0,75 h)**
  - Catálogo de acciones y recomendaciones por regla, en JSON versionado: `env-co2-1h`, `env-pio2`, `env-ptotal`, `env-dpdt`, `env-n2`, `env-rh`, `env-t` y la regla de tendencia.
  - **Todo marcado `DEMO` y etiquetado como ficticio**, con la frase «dato de demostración, no de NASA».
  - Las acciones coinciden con el catálogo de tipos de incidencia (por ejemplo, `revisar_ventilacion_y_filtros` para CO₂).
- [ ] **8.4 Handler de `alert_raised` (0,75 h)**
  - Consumidor `knowledge.on_alert_raised`, idempotente por `(consumer, event_id)`.
  - Construye la recomendación (acciones, citas, estado de evidencia) y publica `recommendation_ready` en la misma transacción.
  - **No espera a ningún modelo.**
- [ ] **8.5 Fachadas y GraphQL (0,5 h)**
  - `ActionCatalogQuery` (título y descripción de una acción, usada por Misiones). `KnowledgeQuery` (búsqueda por texto sobre lo cargado).
  - Resolvers de `knowledgeSearch` registrados en el esquema que compone A.

**Criterios de aceptación**

- Dado un `alert_raised` de `env-co2-1h`, se genera una recomendación con al menos dos acciones y una cita con documento, requisito y estado de evidencia.
- Entregar el mismo evento dos veces **no duplica** la recomendación.
- Con el adaptador demo, toda respuesta lleva la etiqueta `DEMO`.
- Sin Ollama ni red, todo funciona.
- `import-linter` en verde: `knowledge` no importa nada de otro módulo salvo `contracts` y `facade`.

**Pruebas**

- `pytest` de dominio: una recomendación por cada regla del catálogo.
- Prueba de idempotencia con evento duplicado.
- Prueba de contrato: `RecommendationReady` valida contra su modelo Pydantic.

**Hito:** I4 (hora 17). El evento real llega desde A y la recomendación aparece en el panel de alerta.

---

### F12 · RAG sobre PDFs de NASA · 4 h · P1 (cabe antes de la entrega) · RAG

**Objetivo:** que las recomendaciones y respuestas salgan de fragmentos reales de los documentos públicos, con cita verificable.

**Depende de:** F8.

**Documentos de entrada**

| Documento | Estado | Uso |
| --- | --- | --- |
| NASA-STD-3001 Vol. 1 Rev C | Leído (secciones 3 y 4) | Salud de la tripulación, radiación, criterios relativos a la línea base |
| NASA-STD-3001 Vol. 2 Rev F | Leído (sección 6 y parte de 7.1) | Atmósfera, agua, acústica, vibración, radiación, nutrición |
| OCHMO-TB-002 (ECLSS) | Leído | Resumen de atmósfera, agua y soporte vital |
| OCHMO-TB-003 (atmósfera habitable) | Leído | Hipoxia, hiperoxia, descompresión |
| OCHMO-TB-004 (CO₂) | Leído | Síntomas por nivel de CO₂, caso Apolo 13 |
| OCHMO-TB-044 (operaciones médicas) | Leído | Rol del CMO, mareo espacial |
| Checklist del botiquín médico | Leído | Catálogo de acciones y mediciones a bordo |
| Human Integration Design Handbook, OCHMO-STD-100.1A, Manual de emergencias médicas de la ISS | **No abiertos** | Opcionales. El manual viene de una liberación por transparencia: **revisar licencia y vigencia** |

**Tareas**

- [ ] **12.1 Selección y licencia (0,5 h)**
  - Manifiesto `data/knowledge/manifest.json` con código, título, URL, `license_status` y `verification_state` por documento.
  - **No se empaqueta ningún PDF sin confirmar su licencia.** Los dudosos se indexan localmente y se documenta.
- [ ] **12.2 Ingesta (1,25 h)**
  - Comando `python -m spaceapp.knowledge.ingest`: extrae texto por página, detecta referencias de requisito (`[V2 6004]`, `[V1 4033]`, `Tabla 6.2-1`) y fragmenta por requisito o sección con solapamiento corto.
  - Guarda por fragmento: documento, número de requisito, página, contenido y `evidence_state`.
  - **Tablas que vienen como imagen** (Tabla 6.2-1 y figuras): se transcriben a mano o se toman del catálogo de reglas, y se marcan como transcritas.
  - Ingesta idempotente: reejecutarla no duplica fragmentos.
- [ ] **12.3 Búsqueda (0,75 h)**
  - Primero **texto completo** (`tsvector` en español), que no necesita modelo.
  - Vector opcional con pgvector si hay un modelo de embeddings local. **Falta decidir cuál** (sección 11).
  - Umbral mínimo de relevancia: bajo el umbral, no hay pasaje.
- [ ] **12.4 Política de respuesta (0,75 h)**
  - Responder **solo** con pasajes recuperados, con cita obligatoria (documento, requisito, página y estado).
  - Sin pasaje: «No tengo esa información en las fuentes cargadas». **Nunca se inventa un protocolo.**
  - Si el contenido viene del adaptador demo, la respuesta dice «dato de demostración, no de NASA».
  - Cambio de adaptador por perfil: `jurado` usa RAG y cae a demo si falta un pasaje.
- [ ] **12.5 Evaluación (0,5 h)**
  - Conjunto de unas 15 preguntas con el pasaje esperado (CO₂ y cefalea, hipoxia, presión de cabina, mareo espacial, rol del CMO, botiquín, límites de radiación, etc.).
  - Métricas: acierto del pasaje esperado en los 3 primeros y **cero respuestas sin fuente**.
- [ ] **12.6 Buscador de pasajes en la SPA (0,25 h)**
  - Pantalla con búsqueda, lista de pasajes con cita y estado, y enlace al fragmento completo.

**Criterios de aceptación**

- `knowledgeSearch("dolor de cabeza CO₂")` devuelve el fragmento de TB-004 con documento y estado.
- Una pregunta fuera de las fuentes devuelve «No tengo esa información…» y ninguna cita inventada.
- La ingesta completa es repetible y se ejecuta sin internet.
- La evaluación pasa el umbral acordado y no hay respuestas sin fuente.

**Pruebas**

- Pruebas doradas de ingesta (un PDF corto de ejemplo con fragmentos esperados).
- Pruebas de búsqueda con el conjunto de evaluación.
- Prueba de política: pregunta sin pasaje → mensaje de ausencia de información.

---

### F9 · Entrega para el jurado (conjunta con A) · 1,5 h para B · P0

**Objetivo:** que el jurado ejecute todo con un comando, sin internet.

**Depende de:** F5, F7 y F8 (hora 21).

**Tareas de B**

- [ ] **9.1 SPA en la imagen (0,5 h):** compilar `web/` y servirla desde el mismo contenedor (o desde un servidor estático del compose). Variable de entorno de perfil visible en la interfaz.
- [ ] **9.2 Capa de B en Docker (0,5 h):** aislar Ollama y Whisper en su propia capa o contenedor del compose, detrás de puertos con adaptador nulo. Incluir los fragmentos ya indexados y el modelo de Whisper pequeño. Documentar el tamaño final.
- [ ] **9.3 Prueba en otra computadora (0,5 h, con A):** sin internet, sin GPU y con el micrófono bloqueado. La entrada por texto debe funcionar.

**Criterios de aceptación**

- Un solo comando levanta backend, base de datos y SPA con el perfil `jurado`.
- Sin Ollama, la recomendación de plantilla con cita sigue funcionando.
- Sin micrófono, el asistente funciona por texto.

**Hito:** I6 (hora 22,5).

---

### F13 · Asistente: texto y Ollama · 3 h · P1 · RAG

**Objetivo:** que el astronauta pregunte por texto y reciba una respuesta con cita, en streaming.

**Depende de:** F8.

**Contratos**

| Dirección | Contrato |
| --- | --- |
| Expone | GraphQL `askAssistant(text, conversationId)`, `confirmUtterance(id, text)`, `conversation(id)` |
| Publica | `assistant.answer_ready` (`utterance_id`, `text`, `citations[]`) |
| Mensajes WS | `assistant.transcript`, `assistant.token`, `assistant.answer` (los emite el gateway de A a partir de los eventos) |
| Lee | `KnowledgeQuery` (propia) y `ActiveAlertsQuery` de Monitoreo |

**Tareas**

- [ ] **13.1 Módulo y esquema (0,5 h):** esqueleto hexagonal de `assistant`, tablas `conversation` y `utterance`, migración propia.
- [ ] **13.2 Casos de uso GraphQL (0,5 h):** `askAssistant`, `confirmUtterance` y `conversation`, con errores tipados.
- [ ] **13.3 Flujo de respuesta (1 h)**
  - `KnowledgeQuery` → pasajes con cita → `TextComposer` (Ollama) que redacta **solo con lo recuperado**.
  - Tiempo límite de **8 s**: si vence, se responde con los pasajes en texto plano.
  - Streaming de tokens y respuesta final con citas.
  - Contexto de alertas activas: la respuesta puede mencionar la alerta vigente, **sin cambiarla ni decidirla**.
- [ ] **13.4 Puerto `LlmGateway` (0,5 h):** adaptadores Ollama, n8n (opcional) y nulo. El nulo devuelve los pasajes sin redactar.
- [ ] **13.5 Interfaz del asistente (0,5 h):** chat, ejemplos de preguntas, citas con enlace al pasaje, chip de modo («local» o «nube» según el adaptador) y estado «No tengo esa información…».

**Criterios de aceptación**

- «¿Por qué me duele la cabeza?» con CO₂ alto responde con el pasaje de TB-004 y su cita.
- Sin Ollama o con más de 8 s, la respuesta llega igual con los pasajes.
- Una pregunta sin pasaje no produce una respuesta inventada.
- El asistente nunca cambia el estado de una alerta.

**Pruebas**

- `pytest` con un `LlmGateway` falso: tiempo agotado, nulo y streaming.
- Playwright: pregunta con pasaje y pregunta sin pasaje.

---

### F14 · Voz con Whisper · 3 h · P1 · RAG

**Objetivo:** hablar al sistema sin teclear, con confirmación antes de actuar.

**Depende de:** F13.

**Contratos:** REST `POST /api/v1/voice/utterances` (audio `webm` o `wav` y `conversation_id`; responde `202` con `utterance_id`). WebSocket `assistant.transcript`.

**Tareas**

- [ ] **14.1 Puerto `SpeechToText` y Whisper local (1 h):** `faster-whisper` con un modelo pequeño que corra sin GPU. Adaptador nulo para texto.
- [ ] **14.2 Ruta de audio (0,75 h):** guardar el audio, responder `202` de inmediato, transcribir de forma asíncrona y publicar la transcripción para que llegue por WS.
- [ ] **14.3 Interfaz de voz (0,75 h):** botón de mantener para hablar (`MediaRecorder`), transcripción **editable**, botón de confirmar y estado de «escuchando».
- [ ] **14.4 Pruebas con ruido y términos médicos (0,5 h):** audios de ejemplo, palabras como «hipoxia», «ppCO₂», «presión parcial». Entrada por texto siempre disponible.

**Criterios de aceptación**

- Hablar produce una transcripción editable. **No se actúa sin confirmar.**
- Sin Whisper o sin micrófono, el sistema sigue funcionando por texto.
- Una emergencia no depende de la voz.

**Nota técnica:** el navegador solo permite el micrófono en `localhost` o con HTTPS. Documentarlo en el README.

---

### F10 · Tareas, parte de interfaz · 1,5 h · P1

**Objetivo:** que la tripulación vea sus tareas del día, cree las suyas y bloquee las de Tierra con motivo.

**Depende de:** F9. **Mock:** el esquema de tareas ya está congelado. B construye la interfaz sobre mocks hasta que A termine el backend (F10 de A).

**Contratos que consume:** `tasks(kind, status)`, `groundPlan`, `createTask`, `updateTask · deleteTask`, `blockTask`, `completeTask(effective)`, `snoozeReminder`, `setConsent`. WS `task.assigned · reminder.due` y `plan.received · plan.applied`.

**Tareas**

- [ ] **10.1 Lista de tareas (0,5 h):** filtros Todas, Salud, Nave e Incidentes, agrupadas, con **etiqueta de origen** (Tierra, Sistema o Tripulación) en cada tarjeta.
- [ ] **10.2 Nueva tarea propia (0,5 h):** formulario de tipo, zona y título. Editar y eliminar solo las de origen `TRIPULACION`.
- [ ] **10.3 Bloqueo y efectividad (0,25 h):** «No puedo cumplirla» con motivo (no se borra), «¿Funcionó?» al completar y posponer recordatorio.
- [ ] **10.4 Racha, logros y consentimiento (0,25 h):** solo las rutinas de salud suman a la racha. **Las alertas críticas no se gamifican.** Interruptor de la categoría «tareas» en «Enlace y privacidad».

**Criterios de aceptación**

- Una tarea de Tierra no se puede editar ni borrar, solo completar, posponer o bloquear con motivo.
- Una tarea propia se puede crear sin enlace.
- Las medidas de alertas, las de Tierra y los incidentes no suman puntos.

---

### F11 · Panel del centro de control, parte de interfaz · 2 h · P1

**Objetivo:** que el centro de control programe tareas con la opción B: planes versionados con copia local en la nave.

**Depende de:** F9. A termina antes el backend (F11 de A).

**Contratos que consume (rol `ground`):** `groundTasks`, `saveGroundTemplate`, `cancelGroundTemplate`, `publishGroundPlan`, `PUT /api/v1/groundlink/link` (control del enlace en la demo) y los mensajes `plan.received · plan.applied`.

**Tareas**

- [ ] **11.1 Ruta `/ground` y diseño (0,5 h):** la misma SPA con rol `ground`. Dejar claro en la pantalla que es el panel de Tierra.
- [ ] **11.2 Borrador y publicación (0,75 h):** plantillas activas con su estado en la nave (pendiente, recibida, aplicada, completada, bloqueada con motivo), borrador de la versión siguiente, añadir plantilla, marcar para cancelar y **Publicar plan vN**.
- [ ] **11.3 Estado del plan y enlace (0,5 h):** canalización «Publicado → En el enlace → Recibido → Aplicado → Confirmado» y control del enlace con demora para la demo.
- [ ] **11.4 Aviso en la nave (0,25 h):** «Plan vN aplicado» al recibir `plan.applied`.

**Criterios de aceptación**

- Con el enlace cortado, el plan queda «en cola». Al restablecerlo llega, se aplica y se confirma.
- Una versión repetida se ignora, un plan corrupto se rechaza completo y un ítem inválido se rechaza solo él.
- Solo se ve el estado de tareas si la tripulación comparte la categoría «tareas».

**Hito:** I7 (hora 32).

---

### F16 · Alexa como respaldo · 2 h · P2 · RAG

**Objetivo:** tener un adaptador de voz de respaldo para la demo, **solo si Whisper se traba**.

**Depende de:** F14.

**Tareas**

- [ ] **16.1 Skill de desarrollo (0,75 h):** modelo de interacción y cuenta de desarrollo del equipo. Un skill en modo desarrollo corre solo en esa cuenta, y alcanza para la demo.
- [ ] **16.2 Webhook (0,5 h):** `POST /api/v1/alexa/webhook` activo **solo con el perfil `dev2`**. Traduce la intención a `askAssistant`.
- [ ] **16.3 Túnel público (0,5 h):** endpoint accesible para Alexa.
- [ ] **16.4 Documentación (0,25 h):** la interfaz muestra «Voz en la nube: no es autónomo». Se dice así en la presentación.

---

## 4. Diseño de los módulos de B

### 4.1 Contratos públicos de B

**Eventos que B publica** (todos por outbox):

| Evento | Receptores | Payload |
| --- | --- | --- |
| `knowledge.recommendation_ready` | Misiones (A), Gateway (A), Enlace con Tierra (A) | `alert_id`, `recommendation_id`, `action_keys[]`, `citations[]` |
| `knowledge.recommendation_enriched` | Gateway (A) | `recommendation_id`, `text` |
| `assistant.answer_ready` | Gateway (A) | `utterance_id`, `text`, `citations[]` |

**Evento que B consume:** `monitoring.alert_raised` (de A).

**Fachadas de lectura**

| Fachada | Quién la usa | Para qué |
| --- | --- | --- |
| `ActionCatalogQuery` (B) | Misiones (A) | Título y descripción de una acción |
| `KnowledgeQuery` (B) | Asistente (B) | Pasajes citables |
| `RuleQuery` (A) | Conocimiento (B) | Regla y `action_key` de una alerta |
| `ActiveAlertsQuery` (A) | Asistente (B) | Contexto de alertas activas |

**Forma de una cita (`Citation`)**

```graphql
type Citation {
  documentCode: String!
  requirementRef: String
  page: Int
  excerpt: String!
  evidenceState: EvidenceState!   # VERIFICADO | TB | DEMO | NO_VERIFICADO
}
type Recommendation {
  actions: [Action!]!
  body: String!
  citations: [Citation!]!
  composedBy: String!             # plantilla | llm
}
```

### 4.2 Esquemas de datos

**Esquema `knowledge`**

| Tabla | Columnas principales |
| --- | --- |
| `document` | `id`, `code` (único), `title`, `url`, `license_status`, `verification_state`, `ingested_at` |
| `chunk` | `id`, `document_id` (FK), `requirement_ref`, `page`, `content`, `embedding` (opcional), `evidence_state` |
| `action` | `id`, `key` (único), `title`, `description`, `category`, `source_chunk_id` (FK, opcional) |
| `recommendation` | `id`, `alert_id` (referencia blanda a Monitoreo), `source_kind` (`DEMO` o `RAG`), `body`, `citations` (jsonb), `composed_by`, `created_at` |
| `recommendation_action` | `recommendation_id` (FK), `action_id` (FK) |

**Esquema `assistant`**

| Tabla | Columnas principales |
| --- | --- |
| `conversation` | `id`, `crew_member_id` (referencia blanda), `channel` (voz o texto), `created_at` |
| `utterance` | `id`, `conversation_id` (FK), `role` (tripulación o asistente), `text`, `adapter` (whisper, alexa o texto), `confirmed`, `citations` (jsonb), `created_at` |

Reglas: sin claves foráneas hacia otros módulos. `chunk.embedding` es opcional: sin él, se busca por texto completo.

### 4.3 Flujo de recomendación por alerta

1. Llega `monitoring.alert_raised` al handler de Conocimiento (idempotente).
2. Se consulta `RuleQuery` para obtener la regla y su `action_key`.
3. Se busca el pasaje o la acción en la fuente activa (`demo` o `rag`) y se arma la recomendación **de plantilla con cita**.
4. Se guarda y se publica `recommendation_ready` en la misma transacción.
5. **Opcional:** `TextComposer` (Ollama) redacta una explicación con tiempo límite de 8 s y publica `recommendation_enriched`. Si falla o vence, no pasa nada: la plantilla ya está en pantalla.

### 4.4 Qué adaptador activa cada perfil

| Puerto | `dev1` | `dev2` | `jurado` |
| --- | --- | --- | --- |
| Voz de entrada | Whisper local | Alexa (nube, solo demo) | Whisper local |
| Conocimiento | Demo + RAG | Demo + RAG | RAG. Cae a demo si falta un pasaje |
| Redacción | Ollama | Ollama | Ollama. Cae a plantilla si tarda más de 8 s |

El nombre de la variable (`SPACEAPP_PROFILE`) y el valor por defecto `jurado` son una **propuesta** y no una decisión tomada.

---

## 5. Contratos que B consume de A

### 5.1 GraphQL

| Pantalla | Operaciones |
| --- | --- |
| Cabina | `dashboard`, `readings`, `alerts`, `alert`, `rules`, `crewMember`, `acknowledgeAlert`, `recordBaseline`, `setConsent` |
| Nave | `ship`, `incidents`, `incident`, `zoneReadings`, `incidentTypes`, `reportIncident`, `acknowledgeIncident`, `resolveIncident` |
| Tareas | `tasks`, `groundPlan`, `createTask`, `updateTask · deleteTask`, `blockTask`, `completeTask`, `snoozeReminder` |
| Enlace | `groundLinkStatus`, `syncGroundLinkNow`, `setConsent` |
| Panel de Tierra (rol `ground`) | `groundTasks`, `saveGroundTemplate`, `cancelGroundTemplate`, `publishGroundPlan` |

### 5.2 WebSocket (`/ws`)

Mensaje del servidor: `{ "seq": 18342, "topic": "alerts", "type": "alert.raised", "at": "…", "data": { … } }`. `seq` es el `id` del outbox cuando el mensaje nace de un evento. En los ticks es `null`.

| Mensaje | Se usa en |
| --- | --- |
| `telemetry.tick` | Cabina y nave |
| `alert.raised · updated · resolved` | Cabina |
| `recommendation.ready · enriched` | Panel de alerta |
| `incident.opened · updated · resolved`, `zone.status` | Nave |
| `task.assigned · reminder.due` | Tareas |
| `plan.received · applied` | Tareas y panel de Tierra |
| `assistant.transcript · token · answer` | Asistente |
| `groundlink.state` | Enlace |
| `scenario.changed` | Modo demo |
| `subscribe · unsubscribe · resume · ping` | Capa de datos |

**Presión inversa:** cola de 500 mensajes por cliente. Se descartan primero los `telemetry.tick`. **Las alertas no se descartan.**

### 5.3 REST

| Ruta | Uso |
| --- | --- |
| `POST /api/v1/sim/scenarios/{key}:start · :stop` | Modo demo |
| `PUT /api/v1/groundlink/link` | Cortar o restablecer el enlace en la demo |
| `GET /api/v1/rules/catalog.json` | Exportar el catálogo de reglas |

---

## 6. Calidad y pruebas

| Nivel | Qué cubre | Herramienta |
| --- | --- | --- |
| Componentes | `SevPill`, `EvidenceBadge`, gauge, tarjeta de ticket, formulario de reporte | Vitest + Testing Library |
| Capa de datos | `useWs`: resume, duplicados, orden, descarte de ticks sin descartar alertas | Vitest |
| Extremo a extremo con mocks | Escenario → alerta → reconocer. Escenario por zona → ticket → resolver | Playwright |
| Contrato | Tipos generados del esquema. Eventos de B contra sus modelos Pydantic | `graphql-codegen` en CI, `pytest` |
| Conocimiento | Una recomendación por regla, idempotencia, política sin pasaje | `pytest` |
| Ingesta y búsqueda | Pruebas doradas, conjunto de evaluación y cero respuestas sin fuente | `pytest` |
| Asistente | Tiempo límite de 8 s, nulo, streaming | `pytest` con `LlmGateway` falso |
| Accesibilidad | AA, teclado, `aria-live` en alertas, no depender del color | Lighthouse, axe |
| Sin conexión | Contenedor sin red: todo el flujo con el perfil `jurado` | Manual, en otra computadora |

---

## 7. Definición de hecho

Una fase de B está **hecha** cuando:

- [ ] Cumple sus criterios de aceptación.
- [ ] La CI de B está en verde (`eslint`, `tsc`, `vitest`, `ruff`, `mypy`, `import-linter`, `pytest`).
- [ ] No hay valores sin etiqueta de evidencia (`VERIFICADO`, `TB`, `DEMO` o `SIMULADO`).
- [ ] El estado de toda alerta o severidad tiene forma, icono y texto.
- [ ] Funciona sin internet y sin Ollama (adaptador nulo).
- [ ] Hay una nota corta en el README del módulo o de la funcionalidad.
- [ ] Si toca un contrato, el otro desarrollador lo revisó.

---

## 8. Riesgos específicos de B

| Riesgo | Probabilidad | Mitigación |
| --- | --- | --- |
| La API de A tarda y B se bloquea | Alta | Esquema congelado en I0, mocks generados y grabaciones WS. B no depende de A hasta I2 |
| Un cambio de contrato rompe la interfaz sin aviso | Media | Tipos generados en CI: el build falla de inmediato |
| Extracción de texto de los PDFs de mala calidad o tablas como imagen | Alta | Transcripción manual de tablas clave, pruebas doradas y evaluación |
| Ollama lento sin GPU en el equipo del jurado | Alta | La recomendación de plantilla con cita sale primero. Redacción opcional con límite de 8 s |
| Whisper pesado o con mala precisión con términos médicos | Media | Modelo pequeño, confirmación obligatoria y entrada por texto siempre disponible |
| El micrófono falla en Docker o fuera de `localhost` | Media | Documentar HTTPS o `localhost`. Texto como alternativa funcional |
| Licencia de los PDFs para la imagen de Docker | Media | `license_status` por documento y no empaquetar lo dudoso |
| Demasiadas gráficas o SVG vivos a 1 Hz ralentizan la interfaz | Baja | uPlot, coalescencia de ticks y redibujar solo la zona seleccionada |
| Reconexiones del WebSocket generan duplicados o pérdidas | Media | `seq` por mensaje, deduplicación y `resume` desde el último id |
| Si B falta, A no conoce su parte | Media | README corto por módulo y pruebas de contrato como documentación |

---

## 9. Coordinación con Dev A

**Qué le pide B a A**

1. En I0: bus en memoria, repositorio base y contratos congelados.
2. En I1: el outbox real.
3. En I2 a I5: lecturas, incidencias y el gateway reales, para retirar los mocks.
4. Evento `alert_raised` con `zone_id` y la fachada `RuleQuery`.

**Qué le entrega B a A**

1. `recommendation_ready` y la fachada `ActionCatalogQuery` (Misiones las usa).
2. `assistant.answer_ready` para que el gateway lo transforme en mensajes WS.
3. Los resolvers de Conocimiento y Asistente para componer el esquema.

**Cuándo avisar**

- Si un contrato necesita un campo nuevo: **antes** de implementarlo, con una solicitud al dueño.
- Si un mock no refleja el comportamiento real: al detectarlo, no en el hito.
- Al terminar cada fase: una línea con qué quedó listo y qué falta.

---

## 10. Decisiones pendientes que afectan a B

No se deciden sin consultar. Mientras tanto se usa el supuesto indicado.

| # | Decisión | Supuesto actual |
| --- | --- | --- |
| 1 | ¿El RAG solo devuelve pasajes con cita o también redacta con Ollama? | Redacta con Ollama, con caída a plantilla y límite de 8 s |
| 2 | ¿n8n sigue como orquestador o se llama a Ollama directo? | n8n queda como adaptador opcional. Por defecto se llama a Ollama directo |
| 3 | ¿Se sube F12 (RAG completo) a P0? | Sigue en P1, aunque cabe antes de la entrega |
| 4 | Modelo de embeddings local | Ninguno al principio: texto completo. Vector si se decide un modelo |
| 5 | Nombre de la variable de perfil y valor por defecto | `SPACEAPP_PROFILE`, con `jurado` por defecto |
| 6 | Idioma de la interfaz para el jurado | Español. Pendiente si hace falta una versión en inglés |
| 7 | Autenticación del panel de Tierra | Rol `ground` por selección local, sin cuentas externas |
| 8 | Qué documentos extra se indexan (HIDH, OCHMO-STD-100.1A, manual de la ISS) | Solo los siete leídos. Los demás, opcionales y con licencia a revisar |
| 9 | Escenario de la demo (tránsito a Marte, base lunar o ISS) | Nave de tránsito. Cambiar es cambiar datos |

---

## 11. Checklist maestro de Dev B

**Corte P0 (18,5 h)**

- [ ] F0 · Proyecto `web/`, codegen, mocks y contratos revisados (I0)
- [ ] F6 · Panel de cabina, gráficas, cuerpo humano y panel de alerta
- [ ] F7 · Plano, tickets, gráficas por zona, formulario y catálogo de incidencias
- [ ] F8 · Conocimiento con datos de demostración y handler de `alert_raised` (I4)
- [ ] F9 · SPA en la imagen, capa de B en Docker y prueba sin internet (I6)

**P1 y P2 (15,5 h)**

- [ ] F12 · RAG sobre PDFs de NASA: ingesta, búsqueda, política y evaluación
- [ ] F13 · Asistente por texto con Ollama
- [ ] F14 · Voz con Whisper y confirmación
- [ ] F10 · Tareas: lista, nueva tarea, bloqueo con motivo y consentimiento
- [ ] F11 · Panel del centro de control (I7)
- [ ] F16 · Alexa como respaldo (solo si Whisper se traba)

**Cierre**

- [ ] README de `web/`, `knowledge` y `assistant`
- [ ] Guion de demo con los escenarios y el orden de las pantallas
- [ ] Prueba final en otra computadora, sin internet, con el perfil `jurado`
