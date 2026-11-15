import { useId, useState } from 'react'
import { hasChanges, type GroundState, type PlanStage, type TemplateStatus } from './model'

const STAGES: { stage: PlanStage | 'PUBLISHED'; label: string }[] = [
  { stage: 'PUBLISHED', label: 'Published' },
  { stage: 'IN_TRANSIT', label: 'In transit' },
  { stage: 'RECEIVED', label: 'Received' },
  { stage: 'APPLIED', label: 'Applied' },
  { stage: 'CONFIRMED', label: 'Confirmed' },
]

const STATUS_LABELS: Record<TemplateStatus, string> = {
  PENDING: 'Pendiente',
  RECEIVED: 'Recibida',
  APPLIED: 'Aplicada',
  COMPLETED: 'Completada',
  BLOCKED: 'Bloqueada',
}

const DELAYS = [1, 2, 5]

interface GroundPanelProps {
  state: GroundState
  /** Whether the crew shares the "tasks" category. Without it, Ground does not see the status (plan, 11.4). */
  tasksShared: boolean
  onAddTemplate: (template: { title: string; kind: 'HEALTH' | 'SHIP' }) => void
  onCancel: (templateId: string) => void
  onPublish: () => void
  onLink: (change: { online?: boolean; delaySeconds?: number }) => void
}

/** Control center panel (`ground` role): templates, draft, publishing and link. */
export function GroundPanel({
  state,
  tasksShared,
  onAddTemplate,
  onCancel,
  onPublish,
  onLink,
}: GroundPanelProps) {
  const ids = { title: useId(), kind: useId(), delay: useId() }
  const [title, setTitle] = useState('')
  const [kind, setKind] = useState<'HEALTH' | 'SHIP'>('HEALTH')

  const shown = state.draft ?? { version: state.version, templates: state.templates }
  const { published } = state

  return (
    <main>
      <h1>Ground panel (control center)</h1>
      <p>
        This is not the crew screen: from here tasks are scheduled with versioned plans
        that reach the ship over the link, and the ship keeps them in a local copy.
      </p>

      <section aria-label="Link with the ship">
        <p>Link: {state.link.online ? 'connected' : 'cut'}</p>
        <button type="button" onClick={() => onLink({ online: !state.link.online })}>
          {state.link.online ? 'Cortar enlace' : 'Restablecer enlace'}
        </button>
        <label htmlFor={ids.delay}>Link delay</label>
        <select
          id={ids.delay}
          value={state.link.delaySeconds}
          onChange={(event) => onLink({ delaySeconds: Number(event.target.value) })}
        >
          {DELAYS.map((seconds) => (
            <option key={seconds} value={seconds}>
              {seconds}
            </option>
          ))}
        </select>
      </section>

      <section aria-label="Plantillas">
        {state.draft ? (
          <h2>Plan draft v{state.draft.version}</h2>
        ) : (
          <h2>Plan v{state.version} on the ship</h2>
        )}
        {!tasksShared && (
          <p>The crew does not share the status of its tasks with Ground.</p>
        )}
        <ul>
          {shown.templates.map((template) => (
            <li key={template.id} aria-label={template.title}>
              <strong>{template.title}</strong> <span>{template.kind === 'HEALTH' ? 'Health' : 'Ship'}</span>
              {template.cancelled && <span> · Will be cancelled on publish</span>}
              {tasksShared && !state.draft && (
                <>
                  {' '}
                  <span>{STATUS_LABELS[template.status]}</span>
                  {template.status === 'BLOCKED' && template.blockedReason !== null && (
                    <span> · {template.blockedReason}</span>
                  )}
                </>
              )}
              {!template.cancelled && (
                <button type="button" onClick={() => onCancel(template.id)}>
                  Mark to cancel
                </button>
              )}
            </li>
          ))}
        </ul>

        <form
          onSubmit={(event) => {
            event.preventDefault()
            onAddTemplate({ title, kind })
            setTitle('')
          }}
        >
          <label htmlFor={ids.title}>Template title</label>
          <input
            id={ids.title}
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <label htmlFor={ids.kind}>Type</label>
          <select
            id={ids.kind}
            value={kind}
            onChange={(event) => setKind(event.target.value as 'HEALTH' | 'SHIP')}
          >
            <option value="HEALTH">Health</option>
            <option value="SHIP">Ship</option>
          </select>
          <button type="submit" disabled={title.trim() === ''}>
            Add template
          </button>
        </form>

        <button type="button" disabled={!hasChanges(state)} onClick={onPublish}>
          {state.draft ? `Publish plan v${state.draft.version}` : 'Publish plan'}
        </button>
      </section>

      {published && (
        <section aria-label="Plan status">
          <ol aria-label={`Plan status v${published.version}`}>
            {STAGES.map(({ stage, label }) => {
              const reached = STAGES.findIndex((s) => s.stage === published.stage)
              const index = STAGES.findIndex((s) => s.stage === stage)
              const isCurrent =
                stage === published.stage || (published.stage === 'QUEUED' && stage === 'PUBLISHED')
              return (
                <li
                  key={stage}
                  aria-current={isCurrent ? 'step' : undefined}
                  data-reached={published.stage === 'QUEUED' ? index === 0 : index <= reached}
                >
                  {label}
                </li>
              )
            })}
          </ol>
          {published.stage === 'QUEUED' && (
            <p>Queued: no link with the ship. The plan will arrive when it is restored.</p>
          )}
        </section>
      )}
    </main>
  )
}
