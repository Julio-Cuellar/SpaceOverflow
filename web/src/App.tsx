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
import { addCrewTask, blockTask, completeTask, deleteCrewTask, snoozeTask, updateCrewTask } from './app/tasks'
import { bodyIndicatorsFixture } from './data/mocks/body'
import { incidentTypesFixture } from './data/mocks/incidentTypes'
import { tasksFixture } from './data/mocks/tasks'
import { AssistantPanel } from './features/assistant/AssistantPanel'
import { mockAnswer, type AssistantAnswer } from './features/assistant/mockAnswer'
import { SIMULATED_TRANSCRIPT_NOTICE, mockTranscribe } from './features/assistant/mockTranscribe'
import { startMicrophoneRecording } from './features/assistant/microphone'
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

/** Demo profile: demo mode is visible in development and jury (architecture plan, section 12). */
const PROFILE = 'dev1'
/** Fixed demo time: tests do not depend on the clock. */
const NOW = '2026-11-14T10:00:00Z'

type View = 'cabin' | 'ship' | 'assistant' | 'tasks'

/**
 * F6 and F7 wiring with demo data (no backend). When the gateway arrives (I2),
 * the state will come from GraphQL and /ws instead of `initialState`.
 */
export interface AppProps {
  /** Notice from Ground, e.g. "Plan v4 applied" (architecture plan, 11.4). */
  planNotice?: string
  /** Consent for the "tasks" category. If it is not passed, the app keeps it on its own. */
  tasksShared?: boolean
  onTasksSharedChange?: (shared: boolean) => void
  /** Real assistant (backend, n8n and Ollama). Without it, the tab uses the local simulation. */
  askAssistant?: (question: string) => Promise<AssistantAnswer>
  /** Real voice (backend and Whisper). Without it, the tab uses a simulated transcript and says so. */
  transcribeVoice?: (audio: Blob) => Promise<{ text: string } | null>
  /** Reads an answer aloud (backend and Kokoro). Without it, answers are text only. */
  speak?: (text: string) => Promise<void>
}

export function App({
  planNotice,
  tasksShared: sharedProp,
  onTasksSharedChange,
  askAssistant,
  transcribeVoice,
  speak,
}: AppProps = {}) {
  const [state, setState] = useState(initialState)
  const [view, setView] = useState<View>('cabin')
  const [selectedZoneId, setSelectedZoneId] = useState('z-bridge')
  const [presetTypeKey, setPresetTypeKey] = useState<string | undefined>(undefined)
  const [formRound, setFormRound] = useState(0)
  const [tasks, setTasks] = useState(tasksFixture)
  const [localShared, setLocalShared] = useState(true)
  const tasksShared = sharedProp ?? localShared
  const setTasksShared = onTasksSharedChange ?? setLocalShared
  const [nextTaskNumber, setNextTaskNumber] = useState(1)

  const alert = alertFor(state)
  const zones = state.zones.map(({ id, name }) => ({ id, name }))
  const selectedZoneName = zones.find((z) => z.id === selectedZoneId)?.name ?? ''

  return (
    <main>
      <Banner />
      {planNotice && <p role="status" aria-label="Ground plan">{planNotice}</p>}

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
        <button
          type="button"
          role="tab"
          aria-selected={view === 'tasks'}
          onClick={() => setView('tasks')}
        >
          Tasks
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
      ) : view === 'tasks' ? (
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
      ) : view === 'assistant' ? (
        <AssistantPanel
          mode="local"
          speak={speak}
          answerFor={askAssistant ?? ((question) => mockAnswer(question, activeAlertTitles(state)))}
          voice={{
            startRecording: startMicrophoneRecording,
            transcribe: transcribeVoice ?? mockTranscribe,
            notice: transcribeVoice ? undefined : SIMULATED_TRANSCRIPT_NOTICE,
          }}
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
