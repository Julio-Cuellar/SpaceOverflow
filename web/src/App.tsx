import { useState } from 'react'
import {
  acknowledge,
  activeAlertTitles,
  addReportedTicket,
  alertFor,
  dashboardFor,
  initialState,
  normalize,
  provoke,
  zoneSeriesFor,
} from './app/scenario'
import { addCrewTask, blockTask, completeTask, deleteCrewTask, snoozeTask, updateCrewTask } from './app/tasks'
import { bodyIndicatorsFixture } from './data/mocks/body'
import { incidentTypesFixture } from './data/mocks/incidentTypes'
import { tasksFixture } from './data/mocks/tasks'
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
import { ConsentToggle } from './features/tasks/ConsentToggle'
import { NewTaskForm } from './features/tasks/NewTaskForm'
import { TaskList } from './features/tasks/TaskList'
import { Banner } from './shared/ui/Banner'
import { SevPill } from './shared/ui/SevPill'

/** Perfil de demo: el modo demo está visible en desarrollo y jurado (plan, sección 12). */
const PROFILE = 'dev1'
/** Hora fija de la demo: las pruebas no dependen del reloj. */
const NOW = '2026-11-14T10:00:00Z'

type View = 'cabina' | 'nave' | 'asistente' | 'tareas'

/**
 * Cableado de F6 y F7 con datos de demostración (sin backend). Cuando llegue el gateway (I2),
 * el estado vendrá de GraphQL y de /ws en lugar de `initialState`.
 */
export function App() {
  const [state, setState] = useState(initialState)
  const [view, setView] = useState<View>('cabina')
  const [selectedZoneId, setSelectedZoneId] = useState('z-puente')
  const [presetTypeKey, setPresetTypeKey] = useState<string | undefined>(undefined)
  const [formRound, setFormRound] = useState(0)
  const [tasks, setTasks] = useState(tasksFixture)
  const [tasksShared, setTasksShared] = useState(true)
  const [nextTaskNumber, setNextTaskNumber] = useState(1)

  const alert = alertFor(state)
  const zones = state.zones.map(({ id, name }) => ({ id, name }))
  const selectedZoneName = zones.find((z) => z.id === selectedZoneId)?.name ?? ''

  return (
    <main>
      <Banner />

      <div role="tablist" aria-label="Vistas">
        <button type="button" role="tab" aria-selected={view === 'cabina'} onClick={() => setView('cabina')}>
          Cabina
        </button>
        <button type="button" role="tab" aria-selected={view === 'nave'} onClick={() => setView('nave')}>
          Nave
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={view === 'asistente'}
          onClick={() => setView('asistente')}
        >
          Asistente
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={view === 'tareas'}
          onClick={() => setView('tareas')}
        >
          Tareas
        </button>
      </div>

      {view === 'cabina' ? (
        <>
          <CabinPanel dashboard={dashboardFor(state)} />
          {/* La alerta va justo debajo del semáforo: acciones primero (plan, sección 13.2). */}
          {alert &&
            (state.acknowledged ? (
              <p>Alerta reconocida</p>
            ) : (
              <AlertPanel alert={alert} onAcknowledge={() => setState(acknowledge)} />
            ))}
          <BodyMap indicators={bodyIndicatorsFixture} />
        </>
      ) : view === 'tareas' ? (
        <>
          <TaskList
            tasks={tasks}
            zones={zones}
            onComplete={(id, effective) => setTasks((t) => completeTask(t, id, effective))}
            onBlock={(id, reason) => setTasks((t) => blockTask(t, id, reason))}
            onSnooze={(id, minutes) => setTasks((t) => snoozeTask(t, id, minutes))}
            onUpdate={(id, changes) => setTasks((t) => updateCrewTask(t, id, changes))}
            onDelete={(id) => setTasks((t) => deleteCrewTask(t, id))}
          />
          <NewTaskForm
            zones={zones}
            onCreate={(draft) => {
              setTasks((t) => addCrewTask(t, draft, `task-crew-${nextTaskNumber}`))
              setNextTaskNumber((n) => n + 1)
            }}
          />
          <ConsentToggle shared={tasksShared} onChange={setTasksShared} />
        </>
      ) : view === 'asistente' ? (
        <AssistantPanel
          mode="local"
          answerFor={(question) => mockAnswer(question, activeAlertTitles(state))}
        />
      ) : (
        <>
          <DemoPanel
            profile={PROFILE}
            zones={zones}
            onStart={(scenario, zoneId) => setState((s) => provoke(s, scenario, zoneId, NOW))}
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
