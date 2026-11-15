# Especificación del front

> Monitor de salud para astronautas · NASA Space Apps 2026
> Qué pantallas tiene la interfaz, qué datos consume cada una y qué muestra.
> Escrito por Dev A (backend) para que Dev B (interfaz) conecte el front al backend real.
> Fuente de verdad de los contratos: `contracts/schema.generated.graphql`, `contracts/openapi.json` y `contracts/ws-messages.schema.json` (se regeneran con `uv run python -m spaceapp.interfaces.contracts_export`). Si este documento y los contratos discrepan, mandan los contratos.
> Estado al 15 de noviembre de 2026 (versión 2: el backend ya devuelve el código del ticket y los umbrales de las reglas). Lo que el backend **todavía no tiene** está en la sección 9.

## 1. Reglas que valen para todas las pantallas

| Regla | Qué significa en pantalla |
| --- | --- |
| **Aviso fijo** | Siempre visible: «Prototipo de apoyo a la decisión. No es un dispositivo médico» y «Datos simulados» (componente `Banner`). |
| **Origen del dato** | Todo `Vital` trae `origin` (`REAL`, `SIMULATED`, `REPLAY`). Hoy todo es `SIMULATED`: se rotula como simulado. |
| **Estado de evidencia** | Todo dato con norma trae `evidenceState`: `VERIFICADO` (sale de NASA-STD-3001), `TB` (por confirmar), `DEMO` (de demostración), `NO_VERIFICADO`. Se muestra con `EvidenceBadge`. Un dato `DEMO` nunca se presenta como si fuera de NASA. |
| **Semáforo** | `Severity`: `NORMAL`, `ATENCION`, `ALERTA`, `CRITICO`, en ese orden de gravedad. Se muestra con `SevPill`, siempre con texto y no solo con color. |
| **Citas** | Toda recomendación o respuesta del asistente lleva al menos una cita (`documentCode`, `requirementRef`, `excerpt`, `evidenceState`). Sin cita, el asistente dice «No tengo esa información en las fuentes cargadas». |
| **Alertas críticas** | La respuesta a una alerta no se gamifica: sus medidas no suman a la racha. |
| **Errores esperados** | No son excepciones: las mutaciones devuelven una `union` (`...Payload` o `...Error` con `code` y `message`). El front pregunta por `__typename` y muestra `message`. |
| **Fechas** | `DateTime` en ISO 8601 con zona (UTC). `Date` es `AAAA-MM-DD`. La hora de las tareas es la de la nave (UTC). |
| **Idioma** | Textos de la interfaz y mensajes del backend en español. |

## 2. Cómo se conecta

| Canal | Ruta | Para qué |
| --- | --- | --- |
| GraphQL | `POST /graphql` | Todas las lecturas y todas las acciones del usuario. |
| WebSocket | `/ws` | Solo empuje del servidor (alertas, lecturas, tickets, tareas, plan). Las acciones **no** van por aquí. |
| REST | `/health`, `/api/v1/sim/scenarios/{clave}:{start\|stop}` | Perfil de ejecución y modo demo. |

**Desarrollo:** el servidor de Vite hoy solo redirige `/dev` al puerto 8000 y el backend no tiene CORS. Hay que añadir proxy para `/graphql`, `/api` y `/ws` (este último con `ws: true`), o pedir que se active CORS.

**Habitat:** el único hábitat de la demo es `nave-transito`. Cualquier operación que pida `habitatId` acepta ese código o su UUID.

**Identificadores:** todos los `id` son UUID en texto. Los ids de zona del backend **no** son `z-lab` ni `z-puente` (eso es de los mocks): se toman de `ship.zones[].id`.

**Perfil:** `GET /health` devuelve `{"status": "ok", "profile": "jurado" | "dev1" | "dev2"}`. El modo demo (escenarios, sección 4.2) se ve en los tres perfiles, porque el jurado tiene que poder provocarlos. Lo que cambia con el perfil es el lado del backend: las rutas de operación (reencolar eventos y `outboxStats`) solo existen en `dev1` y `dev2`.

**Tipos:** generar los tipos de TypeScript desde `contracts/schema.generated.graphql` y los de los mensajes desde `contracts/ws-messages.schema.json`. `contracts/schema.graphql` es el borrador de Dev B y no se usa más como fuente.

## 3. Mapa de pantallas

| # | Pantalla | Ruta / pestaña | Quién la usa | Datos principales |
| --- | --- | --- | --- | --- |
| 1 | **Cabina** | pestaña «Cabina» | Tripulación | Signos vitales de la cabina, alerta activa con su recomendación, cuerpo humano |
| 2 | **Nave** | pestaña «Nave» | Tripulación | Plano de zonas, gráficas por zona, tickets, catálogo de incidencias, reporte |
| 3 | **Tareas** | pestaña «Tareas» | Tripulación | Tareas del día, racha, tareas propias, consentimiento |
| 4 | **Asistente** | pestaña «Asistente» | Tripulación | Preguntas por texto o voz con respuesta citada |
| 5 | **Panel de Tierra** | `/ground` | Centro de control (rol `ground`) | Plantillas, borrador, publicación y enlace con la nave |
| — | **Aviso de plan** | franja superior | Tripulación | «Plan vN aplicado» |
| — | **Banner** | franja superior | Todos | Aviso de prototipo y datos simulados |

## 4. Pantallas

### 4.1 Cabina

**Qué muestra**

| Elemento | Dato | De dónde sale |
| --- | --- | --- |
| Semáforo global | `globalSeverity` | `dashboard(habitatId: "nave-transito")` |
| Seis signos vitales | `vitals[]`: `key`, `label`, `value`, `unit`, `severity`, `evidenceState`, `origin`, `zoneId` | `dashboard` |
| Panel de alerta (justo bajo el semáforo) | Alerta activa más grave: `ruleKey`, `severity`, `causeHint`, `evidence`, `raisedAt`, `zoneId` | `alerts(first: 20, status: RAISED)` y `alert(id)` |
| Regla de la alerta | `rule`: `sourceRequirement`, `sourceDocument`, `evidenceState`, `parameter` | `alert(id) { rule }` |
| Recomendación | `recommendation`: `body`, `actions[]` (`key`, `title`, `description`), `citations[]`, `sourceKind` | `alert(id) { recommendation }` |
| Cuerpo humano (6 indicadores) | Cabeza, pulmones, corazón, sangre y órganos, temperatura, huesos y músculo | **Sin backend todavía** (sección 9). Se mantiene el mock y se rotula `DEMO`. |

**Los seis signos vitales** (`vitals[].key`): `pressure_kpa` (presión total, kPa), `o2_pct` (oxígeno, %), `co2_mmhg` (CO₂, mmHg), `temperature_c` (temperatura, °C), `humidity_pct` (humedad relativa, %) y `pio2` (oxígeno inspirado, mmHg, calculado de la presión y el oxígeno). Todos con `domain: "cabina"`.

**Cómo se calcula cada uno** (para no sorprenderse):
- Sin alertas, el valor es el promedio de las zonas y `zoneId` es `null`.
- Con alertas, el signo toma la severidad, la zona, el valor y la evidencia de su alerta más grave. Así la tarjeta de CO₂ puede decir «ALERTA en el laboratorio».
- `globalSeverity` es la peor de todas las alertas activas, incluso las que no tienen un signo propio (por ejemplo, nitrógeno).
- Si todavía no hay lecturas, `vitals` viene vacío: mostrar «Sin datos todavía».

**Acción:** botón «Reconocer» → `acknowledgeAlert(id, note)`. Resultado `AlertAcknowledgedPayload { alert, alreadyAcknowledged }` o `AlertError { code: NOT_FOUND | ALREADY_RESOLVED, message }`. Es idempotente: reconocer dos veces no da error, devuelve `alreadyAcknowledged: true`.

**Alertas activas:** no existe un filtro «activas». Se piden `RAISED` y `ACKNOWLEDGED` por separado, o se pide todo y se descartan las `RESOLVED`. Paginación por cursor: `first`, `after` y `pageInfo { hasNextPage, endCursor }`.

**Tiempo real**

| Mensaje de `/ws` | Efecto en la pantalla |
| --- | --- |
| `telemetry.tick` | Actualiza el valor crudo de una métrica. Trae la métrica, no el signo derivado: `pio2` no llega por ticks. |
| `alert.raised` | Aparece el panel de alerta y se vuelve a pedir `dashboard`. |
| `alert.updated` (`status: acknowledged`) | Muestra «Alerta reconocida». |
| `alert.resolved` | Quita el panel y se vuelve a pedir `dashboard`. |
| `recommendation.ready` | Llega la recomendación de plantilla con citas; se vuelve a pedir `alert(id)`. |
| `recommendation.enriched` | Reemplaza el texto por la versión redactada por el modelo (`composed_by: "llm"`). |

**Estrategia recomendada:** pedir `dashboard` al abrir, al recibir cualquier `alert.*` y cada 5 a 10 s. Los ticks sirven para las gráficas (4.2), no para reconstruir el semáforo.

**Estados:** sin conexión al backend → «Sin conexión con la nave»; sin lecturas → «Sin datos todavía»; sin alertas → solo el semáforo.

### 4.2 Nave

**Modo demo (visible en `dev1`, `dev2` y `jurado`)**

| Elemento | Acción | Llamada |
| --- | --- | --- |
| Provocar un escenario | Elige escenario y zona | `POST /api/v1/sim/scenarios/{clave}:start` con cuerpo `{ "zone": "lab", "speed": 1 }` |
| Normalizar | Detiene el escenario | `POST /api/v1/sim/scenarios/{clave}:stop` con `{ "zone": "lab" }` |

Claves de escenario del backend y su botón en el front:

| Botón del front (`DemoPanel`) | Clave actual del front | Clave del backend |
| --- | --- | --- |
| Fuga de presión | `fuga-presion` | `pressure_leak` |
| CO₂ alto | `co2-alto` | `co2_slow` |
| Humedad | `humedad` | `humidity_high` |
| Fallo de O₂ | `fallo-o2` | `o2_failure` |
| Calor | `calor` | `heat` |

`zone` es el **código** de la zona (`lab`, `eng`…), no su id (el front hoy manda el id del mock). `speed` va de 0 (excluido) a 20. Al iniciar, una clave desconocida responde 404 y una zona desconocida 422, con `detail`. Al detener solo se valida la zona; detener un escenario que no está activo no da error.

**Plano de la nave**

| Elemento | Dato | De dónde sale |
| --- | --- | --- |
| Zonas dibujadas | `zones[]`: `id`, `code`, `name`, `kind`, `deck`, `layout { x, y, w, h }` | `ship { zones }` |
| Tamaño del lienzo | `canvas` (`width`, `height`) | `ship { canvas }` |
| Color de cada zona | `status` (`Severity`) y `openIncidents` | `ship`, y en vivo `zone.status` |

El plano es dato: si cambia el JSON del backend (`data/facility/plan.json`), cambian las zonas sin tocar código del front. Diez zonas en la demo: ingeniería, soporte vital, laboratorio, enfermería, puente, esclusa, almacén, gimnasio, cocina y dormitorios. Una zona con `openIncidents > 0` lleva además un icono.

**Gráficas de la zona seleccionada**

| Elemento | Dato | De dónde sale |
| --- | --- | --- |
| Series por métrica | `metric`, `unit`, `points[] { ts, avg, min, max }` | `zoneReadings(zoneId, metrics, from, to, resolution)` |
| Resolución | `MINUTE` (promedio por minuto) o `RAW` (muestras) | argumento `resolution` |
| Métricas disponibles | `pressure_kpa`, `o2_pct`, `co2_mmhg`, `temperature_c`, `humidity_pct` | argumento `metrics` |
| Nuevos puntos en vivo | `zone_id`, `metric`, `value`, `ts` | `telemetry.tick` |
| Líneas de límite | `rules[]`: `parameter`, `kind`, `operator`, `threshold`, `unit`, `windowS`, `severity` | `rules` (una sola vez; el catálogo no cambia durante la sesión) |

**Cómo dibujar los límites:** cada regla de `kind: "umbral"` es una línea horizontal en `threshold`, con `operator` indicando de qué lado está el peligro (`>` o `>=` arriba, `<` o `<=` abajo) y el color de su `severity`. Las reglas de `kind: "tendencia"` (solo `DEMO`) no tienen línea fija: no se dibujan. El parámetro `parameter` dice a qué métrica aplica: `ppco2` es `co2_mmhg`; `humidity_pct`, `temperature_c` y `pressure_kpa` coinciden con la métrica; `pio2`, `n2_pct` y `pressure_rate` son derivados y no tienen gráfica propia. `windowS` es la ventana en segundos durante la que debe sostenerse el valor (0 si es instantáneo).

Las gráficas son por zona. `pio2` no se grafica (se deriva) a menos que el front lo calcule: `PIO₂ = (kPa × 7,50062 − 47) × O₂ % / 100`.

**Tickets**

| Elemento | Dato | De dónde sale |
| --- | --- | --- |
| Lista de tickets, del más nuevo al más viejo | `nodes[]`: `id`, **`code`** (`INC-0001`), `title`, `severity`, `status`, `source`, `zoneId`, `openedAt`, `valuesNormal` | `incidents(first, after, status, zoneId)` |
| Detalle del ticket | `description`, `type { name, categoryName }`, `sourceAlertId`, `updates[] { kind, note, at }` | `incident(id)` |
| Aviso «valores normales, puede cerrarse» | `valuesNormal: true` mientras el ticket sigue abierto | `incident` y `incident.updated` |

El `code` es secuencial y se asigna al abrir el ticket (`INC-0001`, `INC-0002`…); el mismo código viaja en el mensaje `incident.opened`, así que un ticket nuevo se pinta completo sin volver a pedir la lista. Estados: `ABIERTA`, `RECONOCIDA`, `RESUELTA`. Origen: `ALERTA` (automático) o `MANUAL`. **Un ticket automático nunca se cierra solo:** al normalizarse se marca `valuesNormal` y la tripulación lo cierra.

**Acciones sobre un ticket**

| Botón | Mutación | Errores posibles |
| --- | --- | --- |
| Reconocer | `acknowledgeIncident(id)` | `NOT_FOUND`, `ALREADY_RESOLVED` |
| Resolver | `resolveIncident(id, note)` | `NOT_FOUND`, `ALREADY_RESOLVED`, **`ACTIVE_ALERTS`** (un ticket automático no se cierra mientras la zona tenga alertas activas) |

**Catálogo y reporte de incidencias**

| Elemento | Dato | De dónde sale |
| --- | --- | --- |
| Catálogo agrupado por categoría | 61 tipos en 12 categorías: `key`, `category`, `categoryName`, `name`, `detection` (`AUTO`/`MANUAL`), `defaultSeverity`, `evidenceState`, `typicalZones` (códigos de zona o `*`), `suggestedActions[]` | `incidentTypes(category)` |
| Formulario de reporte | zona, tipo, descripción opcional, severidad opcional | `reportIncident(zoneId, typeKey, description, severity)` |

Reglas del formulario: la severidad por defecto es la del tipo; `NORMAL` no es válida (`INVALID_SEVERITY`); zona o tipo inexistentes dan `UNKNOWN_ZONE` o `UNKNOWN_TYPE`. Un reporte manual **no** reemplaza al ticket automático de la zona.

**Tiempo real**

| Mensaje | Efecto |
| --- | --- |
| `zone.status` | Cambia el color de la zona y su contador (`status`, `open_incidents`). |
| `incident.opened` | Aparece el ticket arriba de la lista. |
| `incident.updated` | Cambian severidad, estado o aviso del ticket. |
| `incident.resolved` | El ticket pasa a `RESUELTA`. |
| `scenario.changed` | Indica que un escenario empezó o terminó (`key`, `state`). |

### 4.3 Tareas

**Qué muestra**

| Elemento | Dato | De dónde sale |
| --- | --- | --- |
| Lista de tareas del día, agrupada | `id`, `kind`, `origin`, `title`, `zoneId`, `status`, `dueAt`, `blockedReason`, `effective`, `sourceAlertId`, `incidentId`, `templateId` | `tasks(day, kind, status)` |
| Filtro | Todas, Salud, Nave, Incidentes | argumento `kind` (`SALUD`, `NAVE`, `INCIDENTE`) |
| Racha | Rutinas de salud completadas en el día | `streak(day)` |
| Origen de cada tarea | `TIERRA`, `SISTEMA`, `TRIPULACION` | campo `origin` |
| Aviso de plan de Tierra | `version`, `appliedAt`, `rejected[] { title, reason }` | `groundPlan` |
| Consentimiento «tareas» | Si la tripulación comparte el estado de sus tareas con Tierra | **Sin backend todavía** (sección 9) |

**De dónde nace cada tarea**

| Origen | Cuándo aparece | Ejemplo |
| --- | --- | --- |
| `SISTEMA` · `SALUD`/`NAVE` | Una por plantilla y por día, al pedir `tasks` | «Medir la presión arterial», «Revisar los filtros del laboratorio» |
| `SISTEMA` · `INCIDENTE` | Al abrirse un ticket; se completa sola al resolverlo | «Atender: CO₂ alto» (`incidentId`) |
| `SISTEMA` · `SALUD` con `sourceAlertId` | Una por cada acción recomendada para una alerta | «Ventilar la zona» |
| `TIERRA` | Al aplicarse un plan de Tierra | «Ejercicio de 30 minutos» |
| `TRIPULACION` | La crea la tripulación | «Ordenar el almacén» |

**Acciones**

| Botón | Mutación | Reglas |
| --- | --- | --- |
| Completar | `completeTask(id, effective)` | Cualquier origen. `effective` (`true`/`false`/`null`) responde «¿Funcionó?». Idempotente. |
| Posponer | `snoozeTask(id, minutes)` | De 1 a 1440 minutos; por defecto 15. |
| «No puedo cumplirla» | `blockTask(id, reason)` | El motivo es obligatorio. La tarea no se borra. |
| Crear | `createTask(kind, title, zoneId, dueAt)` | Solo `SALUD` o `NAVE`. Origen `TRIPULACION`. Funciona sin enlace con Tierra. |
| Editar | `updateTask(id, title, zoneId, dueAt)` | Solo tareas `TRIPULACION`; si no, `NOT_EDITABLE`. |
| Borrar | `deleteTask(id)` | Solo tareas `TRIPULACION`; si no, `NOT_DELETABLE`. |

El front ya oculta editar y borrar para tareas que no son propias (`canEdit`, `canDelete`); el backend las rechaza de todos modos.

**Racha:** solo suman las rutinas de `SALUD` completadas que no son de Tierra ni nacieron de una alerta. El backend la calcula para un solo día; el front no necesita recalcularla.

**Tiempo real (topic `crew`):** `task.assigned` (nueva tarea), `task.created` (tarea propia), `task.completed`, `task.blocked`, `groundplan.applied` (se vuelve a pedir `groundPlan` y `tasks`).

### 4.4 Asistente

**Qué muestra**

| Elemento | Dato |
| --- | --- |
| Conversación | Pregunta de la persona y respuesta (`text`) |
| Citas | `citations[]`: `documentCode`, `requirementRef`, `excerpt`, `evidenceState` |
| Sin respaldo | Si no hay pasaje relevante: «No tengo esa información en las fuentes cargadas. No se inventa un protocolo.» |
| Nota de alerta | «Esta respuesta no cambia la alerta.» |
| Entrada | Texto, o voz con transcripción **editable y con confirmación** antes de enviar |
| Aviso de voz | «Transcripción simulada» mientras se use el adaptador de mentira |

**Dónde está hoy:** el asistente **no está en la app principal** (`main.py`). Dev B lo probó con su servidor de desarrollo (`python -m spaceapp.devtools.assistant_server`, puerto 8000). La integración con la app principal es el siguiente paso en la rama `testing`.

**Contrato actual** (`POST /dev/ask`, hoy en el servidor de desarrollo):
- Entrada: `{ "text": "¿Qué pasa si baja el oxígeno?" }`
- Salida: `{ "state", "outcome": "ANSWERED" | "NO_INFO", "text", "composed_by": "template" | "llm", "degraded": boolean, "citations": [...] }`

El front ya lo consume con `askBackend(VITE_ASSISTANT_URL)`. Cuando esté integrado, la ruta definitiva se acuerda entre Dev A y Dev B y se publica en `contracts/openapi.json`. `degraded: true` significa que respondió con los pasajes en texto plano porque n8n u Ollama no contestaron; se muestra igual, con una nota discreta.

**Alternativa solo de búsqueda:** `knowledgeSearch(query, k)` devuelve los pasajes citables sin redactar respuesta (`documentCode`, `excerpt`, `evidenceState`). Sirve para un buscador de protocolos.

**Tiempo real:** `assistant.answer` (topic `assistant`) con `utterance_id`, `text` y `citations`.

### 4.5 Panel de Tierra (`/ground`)

Es la misma aplicación con otra ruta (rol `ground`). **No es la pantalla de la tripulación:** desde aquí se programan tareas con planes versionados que llegan a la nave por el enlace.

**Qué muestra**

| Elemento | Dato | De dónde sale |
| --- | --- | --- |
| Versión del plan en la nave | `appliedVersion` | `groundControl` |
| Plantillas activas y su estado | `templates[]`: `id`, `title`, `kind`, `status`, `blockedReason`, `cancelled` | `groundControl` |
| Borrador del plan | `draft { version, templates[] }` (es `null` si no hay cambios) | `groundControl` |
| Plan publicado y su etapa | `published { version, stage, reason, publishedAt, ackedAt }` | `groundControl` |
| Estado del enlace | `link { online, delaySeconds, changedAt }` | `groundControl` |

**Estado de una plantilla** (`GroundTemplateStatus`): `PENDIENTE` (solo en el borrador), `APLICADA`, `COMPLETADA`, `BLOQUEADA`. El motivo del bloqueo (`blockedReason`) solo se muestra si la tripulación comparte la categoría «tareas» (sección 9).

**Canalización de un plan** (`PlanStage`): `BORRADOR` → `EN_COLA` (enlace cortado) → `EN_EL_ENLACE` → `RECIBIDO` → `APLICADO` → `CONFIRMADO`. Un plan también puede quedar `RECHAZADO` (con `reason`). Mientras haya un plan sin confirmar no se puede publicar otro.

**Acciones**

| Botón | Mutación | Errores |
| --- | --- | --- |
| Agregar plantilla | `saveGroundTemplate(title, kind, zoneCode, recurrence, templateId)` | `TITLE_REQUIRED`, `INVALID_KIND` |
| Cancelar plantilla | `cancelGroundTemplate(templateId)` | `NOT_FOUND` |
| Publicar plan | `publishGroundPlan` | `NOTHING_TO_PUBLISH`, `PLAN_IN_FLIGHT` |
| Cortar o restablecer enlace | `setGroundLink(online, delaySeconds)` | — |

Todas devuelven la vista completa (`GroundControlView`) o un `GroundError`. `kind` solo admite `SALUD` o `NAVE`. `zoneCode` es el código de la zona (`lab`). `recurrence` es `DIARIA` (por defecto) o `UNA_VEZ`. Cancelar una plantilla que solo existe en el borrador la quita; una ya aplicada queda marcada `cancelled` y se retira de la nave al aplicarse el plan. Lo que la tripulación ya completó no se pierde.

**Tiempo real (topic `crew`):** `groundplan.received`, `groundplan.applied`, `groundplan.confirmed` y `groundlink.state` (`UP`/`DOWN`, `queued`). Con ellos la canalización avanza sin sondear.

## 5. Mensajes de `/ws`

**Formato.** Todo mensaje del servidor es `{ "seq", "topic", "type", "at", "data" }`.
- `seq` es el id del outbox cuando el mensaje nace de un evento; en los ticks y en el topic `system` es `null`.
- Los `data` y los nombres de campo de los mensajes están en `snake_case`, a diferencia de GraphQL.

**Topics:** `telemetry`, `alerts`, `habitat`, `crew`, `assistant`. Un cliente nuevo está suscrito a **todos**. Mensajes del cliente:

| Mensaje | Respuesta |
| --- | --- |
| `{ "type": "subscribe", "topics": [...] }` / `unsubscribe` | `subscribed` con la lista de topics vigentes |
| `{ "type": "resume", "after_outbox_id": N }` | Los mensajes perdidos con `seq > N`, en orden, y luego `resumed { count, last_seq }`. Retención de 24 h. |
| `{ "type": "ping", "ts": ... }` | `pong` con el mismo `ts` |
| (cualquier otro) | `error { reason }`; la conexión sigue abierta |

El servidor envía `ping` si pasan 15 s sin mensajes.

**Catálogo**

| Topic | `type` | Campos de `data` |
| --- | --- | --- |
| `telemetry` | `telemetry.tick` | `zone_id`, `sensor_id`, `metric`, `value`, `ts` |
| `telemetry` | `scenario.changed` | `key`, `state`, `speed`, `zone_id` |
| `alerts` | `alert.raised` | `alert_id`, `zone_id`, `rule_key`, `severity`, `evidence_state`, `cause_hint`, `evidence` |
| `alerts` | `alert.updated` | `alert_id`, `status` (`acknowledged`), `at` |
| `alerts` | `alert.resolved` | `alert_id`, `status` (`resolved`), `resolved_at`, `duration_s` |
| `alerts` | `recommendation.ready` | `alert_id`, `recommendation_id`, `action_keys`, `citations`, `composed_by: "template"` |
| `alerts` | `recommendation.enriched` | `recommendation_id`, `text`, `composed_by: "llm"` |
| `habitat` | `incident.opened` | `incident_id`, `code`, `zone_id`, `severity`, `title`, `description`, `source`, `status` |
| `habitat` | `incident.updated` | `incident_id`, `severity`, `status`, `note` |
| `habitat` | `incident.resolved` | `incident_id`, `zone_id`, `resolved_at`, `status` |
| `habitat` | `zone.status` | `zone_id`, `status`, `open_incidents` |
| `crew` | `task.assigned` | `task_id`, `crew_member_id`, `kind`, `origin`, `action_key`, `due_at` |
| `crew` | `task.created` | `task_id`, `kind`, `title`, `zone_id`, `origin` |
| `crew` | `task.completed` | `task_id`, `action_key`, `effective` |
| `crew` | `task.blocked` | `task_id`, `origin`, `reason` |
| `crew` | `groundplan.received` | `batch_id`, `plan_version`, `changes` |
| `crew` | `groundplan.applied` | `plan_version`, `applied`, `rejected` |
| `crew` | `groundplan.confirmed` | `batch_id`, `items`, `acked_at` |
| `crew` | `groundlink.state` | `state`, `since`, `queued` |
| `assistant` | `assistant.answer` | `utterance_id`, `text`, `citations` |
| `system` | `subscribed`, `pong`, `ping`, `resumed`, `error` | según el caso |

**Comportamiento que el front debe respetar**
- **Presión inversa:** cada cliente tiene una cola de 500 mensajes. Si se llena, el servidor descarta primero los ticks; **las alertas nunca se descartan**. Un tick reemplaza al pendiente de la misma zona y métrica, así que solo importa el último valor.
- **Reconexión:** guardar el último `seq` aplicado y enviar `resume` al reconectar. Ignorar cualquier mensaje con `seq` menor o igual al último ya aplicado (el `Stream` de Dev B ya lo hace).
- **Orden:** los mensajes con `seq` llegan en orden creciente.
- **Cuándo no hay `seq`:** los ticks y los mensajes `system`. Todo mensaje nacido de un evento (alertas, recomendaciones, escenarios, tickets, tareas y planes) lleva `seq`.

## 6. Qué reemplaza a cada mock

| Mock de Dev B | Se reemplaza por |
| --- | --- |
| `dashboardFor(state)` y `CabinPanel` | `dashboard(habitatId)` + `alert.*` |
| `alertFor(state)` y `AlertPanel` | `alerts(status: RAISED)` + `alert(id)` + `acknowledgeAlert` |
| `bodyIndicatorsFixture` | Sin reemplazo todavía (sección 9) |
| `state.zones`, `ShipPlan` | `ship { zones, canvas }` + `zone.status` |
| `zoneSeriesFor`, `ZoneCharts` | `zoneReadings` + `telemetry.tick` |
| `state.tickets`, lista de tickets | `incidents` + `incident.*` |
| `incidentTypesFixture`, `CatalogList` | `incidentTypes` |
| `addReportedTicket`, `ReportForm` | `reportIncident` |
| `provoke` / `normalize`, `DemoPanel` | `POST /api/v1/sim/scenarios/{clave}:start` y `:stop` |
| `tasksFixture` y `app/tasks.ts` | `tasks`, `streak` y las mutaciones de tareas |
| `Root.tsx` con `GroundState` en memoria | `groundControl` y las mutaciones de Tierra, más los mensajes `groundplan.*` |
| `askBackend` / `mockAnswer` | Ruta del asistente integrada en la app principal |

## 7. Diferencias de nombres y tipos entre el front actual y el backend

| Tema | Front de Dev B hoy | Backend |
| --- | --- | --- |
| Id de zona | `z-lab`, `z-puente` (mock) | UUID de `ship.zones[].id`; `code` (`lab`) para plantillas y escenarios |
| Umbrales de las reglas | Rangos fijos dentro del front (`bands` en el artefacto) | `rules { operator threshold unit windowS }`: la fuente es el backend |
| Claves de escenario | `fuga-presion`, `co2-alto`, `humedad`, `fallo-o2`, `calor` | `pressure_leak`, `co2_slow`, `humidity_high`, `o2_failure`, `heat` |
| Código visible del ticket | `t.code` (por ejemplo «INC-001») | `code` con **cuatro dígitos** (`INC-0001`). Ajustar si el front o sus pruebas esperan tres |
| Estado de plantilla de Tierra | `PENDIENTE`, `RECIBIDA`, `APLICADA`, `COMPLETADA`, `BLOQUEADA` | `PENDIENTE`, `APLICADA`, `COMPLETADA`, `BLOQUEADA`: **no existe `RECIBIDA`** |
| Etapa del plan | `EN_COLA`, `EN_EL_ENLACE`, `RECIBIDO`, `APLICADO`, `CONFIRMADO` | Las mismas, más `BORRADOR` y **`RECHAZADO`** (el front debe mostrarlo) |
| Tipo de plantilla | `SALUD` o `NAVE` | `TaskKind` incluye `INCIDENTE`, pero una plantilla solo admite `SALUD` o `NAVE` |
| Posponer | `snoozeTask(minutes)` | `snoozeTask(id, minutes)` (no existe `snoozeReminder`) |
| Nombres de campo | `camelCase` | GraphQL en `camelCase`; los `data` de `/ws` en `snake_case` |
| Severidad | `NORMAL`, `ATENCION`, `ALERTA`, `CRITICO` | Igual (en `/ws` también va en mayúsculas) |
| `evidence` de una alerta | — | Objeto libre (`JSON`) con `parameter`, `value`, `unit`, `operator`, `threshold`, `window_s`, `band`, `source_requirement`, `source_document`, `evidence_state`. Mostrar los que existan. |

## 8. Orden recomendado para conectar

1. **Proxy y tipos:** agregar proxy de `/graphql`, `/api` y `/ws`; generar tipos desde `contracts/`.
2. **Cabina:** `dashboard` + `alerts` + `acknowledgeAlert` + mensajes `alert.*`. Es lo primero que ve el jurado.
3. **Nave:** `ship`, `incidents`, `incidentTypes`, `reportIncident`, `zoneReadings`, mensajes `zone.status` e `incident.*`, y el modo demo.
4. **Tareas:** `tasks`, `streak` y las mutaciones; mensajes `task.*`.
5. **Panel de Tierra:** `groundControl` y las mutaciones; mensajes `groundplan.*`.
6. **Asistente:** cuando Dev A lo conecte a la app principal.

En cada paso, quitar el mock correspondiente y dejar las pruebas contra respuestas reales grabadas (los contratos están en `contracts/`).

## 9. Lo que el backend todavía no tiene

| Hueco | Efecto en el front | Qué se propone |
| --- | --- | --- |
| **Cuerpo humano** (6 indicadores) | No hay telemetría ni línea base del cuerpo. | Mantener `bodyIndicatorsFixture` rotulado `DEMO`. Es lo que pide el plan mientras no exista el módulo de Tripulación. |
| **Consentimiento «tareas»** | El interruptor no se guarda en el backend. | Estado local del front. Tierra ve el motivo de bloqueo de las tareas sin filtrar. |
| **Línea base y perfiles de tripulante** (`crewMember`, `recordBaseline`, `setConsent`) | No existen. Todas las tareas pertenecen a un tripulante de demostración. | Pendiente de Tripulación (F15). |
| **Autenticación del rol `ground`** | Cualquiera que abra `/ground` ve el panel. | Aceptable para la demo; se declara en la entrega. |
| **Asistente en la app principal** | El front usa el servidor de desarrollo. | Integración en `testing`: Dev A lo conecta a `main.py`. |
| **DataLoaders y límite de costo** | `incident { updates }` hace una consulta por ticket. | No es problema con pocos tickets; se arregla si hace falta. |
| **Filtro «alertas activas»** | No existe. | Pedir `RAISED` y `ACKNOWLEDGED`. |
| **Recomendaciones en memoria** | Se pierden al reiniciar el backend. | Dev B es dueño de la persistencia. |

## 10. Cómo levantar el backend para probar

```bash
cd SpaceOverflow
docker compose -f docker/compose.yaml up -d --wait postgres      # PostgreSQL en el puerto 5433
for m in platform monitoring telemetry facility engagement groundlink; do
  uv run python -m spaceapp.platform.migrate $m
done
SPACEAPP_PROFILE=dev1 SPACEAPP_RELAY_ENABLED=true SPACEAPP_SIMULATOR_AUTOSTART=true \
  SPACEAPP_RULE_WINDOW_SCALE=0.0167 \
  uv run uvicorn --factory spaceapp.main:create_app --port 8001
```

- `SPACEAPP_PROFILE=dev1` activa el modo demo y las rutas de operación.
- `SPACEAPP_RELAY_ENABLED=true` enciende el relay del outbox: sin él no llegan mensajes por `/ws`.
- `SPACEAPP_SIMULATOR_AUTOSTART=true` enciende el simulador de telemetría.
- `SPACEAPP_RULE_WINDOW_SCALE=0.0167` acorta las ventanas de las reglas (de 1 h a unos 60 s) para que la demostración sea visible. `1` usa los valores de la norma.
- El puerto 8001 evita chocar con el servidor del asistente de Dev B (8000). Proxy de Vite sugerido: `/graphql`, `/api` y `/ws` hacia `http://127.0.0.1:8001`.
- El esquema y los mensajes se pueden explorar en `http://127.0.0.1:8001/graphql` (GraphiQL) y `/docs` (REST).
