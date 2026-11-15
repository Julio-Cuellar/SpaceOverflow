import { dashboardFixture, type DashboardView } from '../data/mocks/fixtures'
import type { AlertView } from '../features/cabin/AlertPanel'
import type { ReportPayload } from '../features/ship/ReportForm'
import type { Ticket, Zone } from '../features/ship/model'
import type { ZoneSeries } from '../features/ship/ZoneCharts'
import { type Severity, severityMeta } from '../shared/lib/severity'

/** Escenarios que el modo demo puede provocar en una zona (plan, sección 7.7). */
const DEMO_SCENARIOS: Record<string, { title: string; severity: Severity }> = {
  'co2-alto': { title: 'CO₂ alto', severity: 'ALERTA' },
  'fuga-presion': { title: 'Fuga de presión', severity: 'CRITICO' },
  humedad: { title: 'Humedad fuera de rango', severity: 'ATENCION' },
  'fallo-o2': { title: 'Fallo de O₂', severity: 'CRITICO' },
  calor: { title: 'Temperatura fuera de rango', severity: 'ATENCION' },
}

const BASE_ZONES: Zone[] = [
  { id: 'z-puente', name: 'Puente de control', layout: { x: 0, y: 0, w: 130, h: 60 }, status: 'NORMAL' },
  { id: 'z-lab', name: 'Laboratorio', layout: { x: 140, y: 0, w: 130, h: 60 }, status: 'NORMAL' },
  { id: 'z-esclusa', name: 'Esclusa', layout: { x: 280, y: 0, w: 130, h: 60 }, status: 'NORMAL' },
  { id: 'z-cocina', name: 'Cocina y comedor', layout: { x: 0, y: 70, w: 130, h: 60 }, status: 'NORMAL' },
  { id: 'z-dormitorios', name: 'Dormitorios', layout: { x: 140, y: 70, w: 130, h: 60 }, status: 'NORMAL' },
  { id: 'z-almacen', name: 'Almacén', layout: { x: 280, y: 70, w: 130, h: 60 }, status: 'NORMAL' },
]

/** Alerta de CO₂ con sus acciones del catálogo DEMO (dato de demostración, no de NASA). */
const CO2_ALERT: AlertView = {
  severity: 'ALERTA',
  ruleText: 'El promedio de 1 hora de ppCO₂ supera el límite de 3 mmHg de la norma.',
  measured: 'ppCO₂ 3.4 mmHg',
  causeHint: 'AMBIENTE',
  actions: [
    {
      key: 'revisar_ventilacion_y_filtros',
      title: 'Revisar ventilación y filtros de CO₂',
      description: 'Comprobar que los ventiladores y los filtros de CO₂ funcionan y no están saturados.',
    },
    {
      key: 'medir_co2_en_zonas_locales',
      title: 'Medir CO₂ en zonas locales',
      description: 'Usar un sensor portátil en la zona donde sube el valor.',
    },
  ],
  source: { documentCode: 'NASA-STD-3001 Vol. 2 Rev F', requirementRef: 'V2 6004', evidenceState: 'VERIFICADO' },
  escalateWhen: 'Si el valor sigue por encima de 3 mmHg tras revisar la ventilación.',
  body: 'Esta recomendación usa un dato de demostración, no de NASA.',
}

export interface AppState {
  /** Clave del último escenario provocado, o 'normal'. */
  scenario: string
  zones: Zone[]
  tickets: Ticket[]
  acknowledged: boolean
}

export function initialState(): AppState {
  return { scenario: 'normal', zones: BASE_ZONES, tickets: [], acknowledged: false }
}

/** Código del ticket: INC-0001, INC-0002… en orden de llegada. */
function nextCode(tickets: readonly Ticket[]): string {
  return `INC-${String(tickets.length + 1).padStart(4, '0')}`
}

export function provoke(state: AppState, scenarioKey: string, zoneId: string, now: string): AppState {
  const demo = DEMO_SCENARIOS[scenarioKey]
  if (!demo) return state

  const code = nextCode(state.tickets)
  const ticket: Ticket = {
    id: code,
    code,
    title: demo.title,
    severity: demo.severity,
    status: 'ABIERTO',
    zoneId,
    source: 'ALERTA',
    openedAt: now,
    valuesInRange: false,
  }
  return {
    scenario: scenarioKey,
    zones: state.zones.map((z) => (z.id === zoneId ? { ...z, status: demo.severity } : z)),
    tickets: [...state.tickets, ticket],
    acknowledged: false,
  }
}

/** Devuelve las zonas a normal y deja los tickets automáticos listos para resolverse. */
export function normalize(state: AppState): AppState {
  return {
    scenario: 'normal',
    zones: state.zones.map((z) => ({ ...z, status: 'NORMAL' })),
    tickets: state.tickets.map((t) => (t.source === 'ALERTA' ? { ...t, valuesInRange: true } : t)),
    acknowledged: false,
  }
}

export function acknowledge(state: AppState): AppState {
  return { ...state, acknowledged: true }
}

/** Un reporte manual abre un ticket; la zona no cambia de estado porque no hay medida. */
export function addReportedTicket(state: AppState, payload: ReportPayload, now: string): AppState {
  const code = nextCode(state.tickets)
  const ticket: Ticket = {
    id: code,
    code,
    title: payload.title,
    severity: payload.severity,
    status: 'ABIERTO',
    zoneId: payload.zoneId,
    source: 'MANUAL',
    openedAt: now,
    valuesInRange: true,
  }
  return { ...state, tickets: [...state.tickets, ticket] }
}

export function dashboardFor(state: AppState): DashboardView {
  return dashboardFixture(state.scenario === 'co2-alto' ? 'co2-alto' : 'normal')
}

export function alertFor(state: AppState): AlertView | null {
  return state.scenario === 'co2-alto' ? CO2_ALERT : null
}

/**
 * Alertas automáticas abiertas con valores aún fuera de rango. El asistente puede nombrarlas;
 * no tiene forma de cambiarlas.
 */
export function activeAlertTitles(state: AppState): string[] {
  return state.tickets
    .filter((t) => t.source === 'ALERTA' && !t.valuesInRange && t.status !== 'RESUELTO')
    .map((t) => `${t.title} (${severityMeta(t.severity).label})`)
}

/** Series de las seis métricas de una zona. Una zona en alerta muestra el CO₂ por encima del umbral. */
export function zoneSeriesFor(state: AppState, zoneId: string): Record<string, ZoneSeries> {
  const zone = state.zones.find((z) => z.id === zoneId)
  const inAlert = zone !== undefined && zone.status !== 'NORMAL'
  const flat = (v: number) => [
    { t: 0, v },
    { t: 30, v },
    { t: 60, v },
  ]

  return {
    o2: { label: 'O₂ (PIO₂)', unit: 'mmHg', points: flat(149.7), evidenceState: 'VERIFICADO' },
    co2: {
      label: 'CO₂ (ppCO₂)',
      unit: 'mmHg',
      points: flat(inAlert ? 3.4 : 1.2),
      evidenceState: 'VERIFICADO',
      threshold: { value: 3, label: 'Umbral 3 mmHg' },
      anomaly: inAlert,
    },
    n2: { label: 'N₂', unit: '%', points: flat(78), evidenceState: 'DEMO' },
    humedad: { label: 'Humedad', unit: '%', points: flat(45), evidenceState: 'DEMO' },
    temperatura: { label: 'Temperatura', unit: '°C', points: flat(22), evidenceState: 'DEMO' },
    presion: { label: 'Presión', unit: 'kPa', points: flat(101.3), evidenceState: 'DEMO' },
  }
}
