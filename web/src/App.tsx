import { useState } from 'react'
import {
  acknowledge,
  activeAlertTitles,
  addReportedTicket,
  alertFor,
  dashboardFor,
  initialState,
  normalize,
  trigger,
  zoneSeriesFor,
} from './app/scenario'
import { bodyIndicatorsFixture } from './data/mocks/body'
import { incidentTypesFixture } from './data/mocks/incidentTypes'
import { AssistantPanel } from './features/assistant/AssistantPanel'
import { mockAnswer } from './features/assistant/mockAnswer'
import { AlertPanel } from './features/cabin/AlertPanel'
import { BodyMap } from './features/cabin/BodyMap'
import { CabinPanel } from './features/cabin/CabinPanel'
import { CatalogList } from './features/ship/CatalogList'
import { DemoPanel } from './features/ship/DemoPanel'
import { ReportForm } from './features/ship/ReportForm'
import { ShipPlan } from './features/ship/ShipPlan'
import { sortTickets } from './features/ship/model'
import { ZoneCharts } from './features/ship/ZoneCharts'
import { Banner } from './shared/ui/Banner'
import { SevPill } from './shared/ui/SevPill'

/** Demo profile: demo mode is visible in development and jury (architecture plan, section 12). */
const PROFILE = 'dev1'
/** Fixed demo time: tests do not depend on the clock. */
const NOW = '2026-11-14T10:00:00Z'

type View = 'cabin' | 'ship' | 'assistant'

/**
 * F6 and F7 wiring with demo data (no backend). When the gateway arrives (I2),
 * the state will come from GraphQL and /ws instead of `initialState`.
 */
export function App() {
  const [state, setState] = useState(initialState)
  const [view, setView] = useState<View>('cabin')
  const [selectedZoneId, setSelectedZoneId] = useState('z-bridge')
  const [presetTypeKey, setPresetTypeKey] = useState<string | undefined>(undefined)
  const [formRound, setFormRound] = useState(0)

  const alert = alertFor(state)
  const zones = state.zones.map(({ id, name }) => ({ id, name }))
  const selectedZoneName = zones.find((z) => z.id === selectedZoneId)?.name ?? ''

  return (
    <main>
      <Banner />

      <div role="tablist" aria-label="Views">
        <button type="button" role="tab" aria-selected={view === 'cabin'} onClick={() => setView('cabin')}>
          Cabin
        </button>
        <button type="button" role="tab" aria-selected={view === 'ship'} onClick={() => setView('ship')}>
          Ship
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={view === 'assistant'}
          onClick={() => setView('assistant')}
        >
          Assistant
        </button>
      </div>

      {view === 'cabin' ? (
        <>
          <CabinPanel dashboard={dashboardFor(state)} />
          {/* The alert goes right below the status light: actions first (architecture plan, section 13.2). */}
          {alert &&
            (state.acknowledged ? (
              <p>Alert acknowledged</p>
            ) : (
              <AlertPanel alert={alert} onAcknowledge={() => setState(acknowledge)} />
            ))}
          <BodyMap indicators={bodyIndicatorsFixture} />
        </>
      ) : view === 'assistant' ? (
        <AssistantPanel
          mode="local"
          answerFor={(question) => mockAnswer(question, activeAlertTitles(state))}
        />
      ) : (
        <>
          <DemoPanel
            profile={PROFILE}
            zones={zones}
            onStart={(scenario, zoneId) => setState((s) => trigger(s, scenario, zoneId, NOW))}
            onNormalize={() => setState(normalize)}
          />

          <ShipPlan zones={state.zones} tickets={state.tickets} onSelectZone={setSelectedZoneId} />

          <ZoneCharts
            key={selectedZoneId}
            zoneName={selectedZoneName}
            series={zoneSeriesFor(state, selectedZoneId)}
          />

          <ol aria-label="Tickets">
            {sortTickets(state.tickets).map((t) => (
              <li key={t.id}>
                {t.code} · {t.title} <SevPill level={t.severity} /> {t.status}
              </li>
            ))}
          </ol>

          <CatalogList
            types={incidentTypesFixture}
            onReport={(typeKey) => {
              setPresetTypeKey(typeKey)
              setFormRound((n) => n + 1)
            }}
          />

          <ReportForm
            key={formRound}
            types={incidentTypesFixture}
            zones={zones}
            presetTypeKey={presetTypeKey}
            onReport={(payload) => setState((s) => addReportedTicket(s, payload, NOW))}
          />
        </>
      )}
    </main>
  )
}
