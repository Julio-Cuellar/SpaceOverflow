import { dashboardFixture, type DashboardView } from '../data/mocks/fixtures'
import type { AlertView } from '../features/cabin/AlertPanel'
import type { ReportPayload } from '../features/ship/ReportForm'
import type { Ticket, Zone } from '../features/ship/model'
import type { ZoneSeries } from '../features/ship/ZoneCharts'
import { type Severity, severityMeta } from '../shared/lib/severity'

/** Scenarios that demo mode can trigger in a zone (architecture plan, section 7.7). */
const DEMO_SCENARIOS: Record<string, { title: string; severity: Severity }> = {
  'co2_slow': { title: 'High CO₂', severity: 'ALERT' },
  'pressure_leak': { title: 'Pressure leak', severity: 'CRITICAL' },
  humidity_high: { title: 'Humidity out of range', severity: 'ATTENTION' },
  'o2_failure': { title: 'O₂ failure', severity: 'CRITICAL' },
  heat: { title: 'Temperature out of range', severity: 'ATTENTION' },
}

const BASE_ZONES: Zone[] = [
  { id: 'z-bridge', name: 'Bridge', layout: { x: 0, y: 0, w: 130, h: 60 }, status: 'NORMAL' },
  { id: 'z-lab', name: 'Laboratory', layout: { x: 140, y: 0, w: 130, h: 60 }, status: 'NORMAL' },
  { id: 'z-airlock', name: 'Airlock', layout: { x: 280, y: 0, w: 130, h: 60 }, status: 'NORMAL' },
  { id: 'z-galley', name: 'Galley and mess', layout: { x: 0, y: 70, w: 130, h: 60 }, status: 'NORMAL' },
  { id: 'z-quarters', name: 'Crew quarters', layout: { x: 140, y: 70, w: 130, h: 60 }, status: 'NORMAL' },
  { id: 'z-storage', name: 'Storage', layout: { x: 280, y: 70, w: 130, h: 60 }, status: 'NORMAL' },
]

/** CO₂ alert with its actions from the DEMO catalog (demo data, not NASA data). */
const CO2_ALERT: AlertView = {
  severity: 'ALERT',
  ruleText: 'The 1-hour average ppCO₂ exceeds the standard limit of 3 mmHg.',
  measured: 'ppCO₂ 3.4 mmHg',
  causeHint: 'ENVIRONMENT',
  actions: [
    {
      key: 'check_ventilation_and_filters',
      title: 'Check ventilation and CO₂ filters',
      description: 'Check that the fans and CO₂ filters are working and not saturated.',
    },
    {
      key: 'measure_co2_in_local_zones',
      title: 'Measure CO₂ in local zones',
      description: 'Use a portable sensor in the zone where the value is rising.',
    },
  ],
  source: { documentCode: 'NASA-STD-3001 Vol. 2 Rev F', requirementRef: 'V2 6004', evidenceState: 'VERIFIED' },
  escalateWhen: 'If the value stays above 3 mmHg after checking ventilation.',
  body: 'This recommendation uses demo data, not NASA data.',
}

export interface AppState {
  /** Key of the last triggered scenario, or 'normal'. */
  scenario: string
  zones: Zone[]
  tickets: Ticket[]
  acknowledged: boolean
}

export function initialState(): AppState {
  return { scenario: 'normal', zones: BASE_ZONES, tickets: [], acknowledged: false }
}

/** Ticket code: INC-0001, INC-0002… in order of arrival. */
function nextCode(tickets: readonly Ticket[]): string {
  return `INC-${String(tickets.length + 1).padStart(4, '0')}`
}

export function trigger(state: AppState, scenarioKey: string, zoneId: string, now: string): AppState {
  const demo = DEMO_SCENARIOS[scenarioKey]
  if (!demo) return state

  const code = nextCode(state.tickets)
  const ticket: Ticket = {
    id: code,
    code,
    title: demo.title,
    severity: demo.severity,
    status: 'OPEN',
    zoneId,
    source: 'ALERT',
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

/** Returns the zones to normal and leaves the automatic tickets ready to be resolved. */
export function normalize(state: AppState): AppState {
  return {
    scenario: 'normal',
    zones: state.zones.map((z) => ({ ...z, status: 'NORMAL' })),
    tickets: state.tickets.map((t) => (t.source === 'ALERT' ? { ...t, valuesInRange: true } : t)),
    acknowledged: false,
  }
}

export function acknowledge(state: AppState): AppState {
  return { ...state, acknowledged: true }
}

/** A manual report opens a ticket; the zone status does not change because there is no measurement. */
export function addReportedTicket(state: AppState, payload: ReportPayload, now: string): AppState {
  const code = nextCode(state.tickets)
  const ticket: Ticket = {
    id: code,
    code,
    title: payload.title,
    severity: payload.severity,
    status: 'OPEN',
    zoneId: payload.zoneId,
    source: 'MANUAL',
    openedAt: now,
    valuesInRange: true,
  }
  return { ...state, tickets: [...state.tickets, ticket] }
}

export function dashboardFor(state: AppState): DashboardView {
  return dashboardFixture(state.scenario === 'co2_slow' ? 'co2_slow' : 'normal')
}

export function alertFor(state: AppState): AlertView | null {
  return state.scenario === 'co2_slow' ? CO2_ALERT : null
}

/**
 * Open automatic alerts whose values are still out of range. The assistant may name them;
 * it has no way to change them.
 */
export function activeAlertTitles(state: AppState): string[] {
  return state.tickets
    .filter((t) => t.source === 'ALERT' && !t.valuesInRange && t.status !== 'RESOLVED')
    .map((t) => `${t.title} (${severityMeta(t.severity).label})`)
}

/** Series for the six metrics of a zone. A zone in alert shows CO₂ above the threshold. */
export function zoneSeriesFor(state: AppState, zoneId: string): Record<string, ZoneSeries> {
  const zone = state.zones.find((z) => z.id === zoneId)
  const inAlert = zone !== undefined && zone.status !== 'NORMAL'
  const flat = (v: number) => [
    { t: 0, v },
    { t: 30, v },
    { t: 60, v },
  ]

  return {
    o2: { label: 'O₂ (PIO₂)', unit: 'mmHg', points: flat(149.7), evidenceState: 'VERIFIED' },
    co2: {
      label: 'CO₂ (ppCO₂)',
      unit: 'mmHg',
      points: flat(inAlert ? 3.4 : 1.2),
      evidenceState: 'VERIFIED',
      threshold: { value: 3, label: 'Threshold 3 mmHg' },
      anomaly: inAlert,
    },
    n2: { label: 'N₂', unit: '%', points: flat(78), evidenceState: 'DEMO' },
    humidity: { label: 'Humidity', unit: '%', points: flat(45), evidenceState: 'DEMO' },
    temperature: { label: 'Temperature', unit: '°C', points: flat(22), evidenceState: 'DEMO' },
    pressure: { label: 'Pressure', unit: 'kPa', points: flat(101.3), evidenceState: 'DEMO' },
  }
}
