import { useId, useState } from 'react'
import { hasChanges, type GroundState, type PlanStage, type TemplateStatus } from './model'

const STAGES: { stage: PlanStage | 'PUBLICADO'; label: string }[] = [
  { stage: 'PUBLICADO', label: 'Publicado' },
  { stage: 'EN_EL_ENLACE', label: 'En el enlace' },
  { stage: 'RECIBIDO', label: 'Recibido' },
  { stage: 'APLICADO', label: 'Aplicado' },
  { stage: 'CONFIRMADO', label: 'Confirmado' },
]

const STATUS_LABELS: Record<TemplateStatus, string> = {
  PENDIENTE: 'Pendiente',
  RECIBIDA: 'Recibida',
  APLICADA: 'Aplicada',
  COMPLETADA: 'Completada',
  BLOQUEADA: 'Bloqueada',
}

const DELAYS = [1, 2, 5]

interface GroundPanelProps {
  state: GroundState
  /** Si la tripulación comparte la categoría «tareas». Sin ella, Tierra no ve el estado (plan, 11.4). */
  tasksShared: boolean
  onAddTemplate: (template: { title: string; kind: 'SALUD' | 'NAVE' }) => void
  onCancel: (templateId: string) => void
  onPublish: () => void
  onLink: (change: { online?: boolean; delaySeconds?: number }) => void
}

/** Panel del centro de control (rol `ground`): plantillas, borrador, publicación y enlace. */
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
  const [kind, setKind] = useState<'SALUD' | 'NAVE'>('SALUD')

  const shown = state.draft ?? { version: state.version, templates: state.templates }
  const { published } = state

  return (
    <main>
      <h1>Panel de Tierra (centro de control)</h1>
      <p>
        No es la pantalla de la tripulación: desde aquí se programan tareas con planes versionados
        que llegan a la nave por el enlace, y la nave los guarda en una copia local.
      </p>

      <section aria-label="Enlace con la nave">
        <p>Enlace: {state.link.online ? 'conectado' : 'cortado'}</p>
        <button type="button" onClick={() => onLink({ online: !state.link.online })}>
          {state.link.online ? 'Cortar enlace' : 'Restablecer enlace'}
        </button>
        <label htmlFor={ids.delay}>Demora del enlace</label>
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
          <h2>Borrador del plan v{state.draft.version}</h2>
        ) : (
          <h2>Plan v{state.version} en la nave</h2>
        )}
        {!tasksShared && (
          <p>La tripulación no comparte el estado de sus tareas con Tierra.</p>
        )}
        <ul>
          {shown.templates.map((template) => (
            <li key={template.id} aria-label={template.title}>
              <strong>{template.title}</strong> <span>{template.kind === 'SALUD' ? 'Salud' : 'Nave'}</span>
              {template.cancelled && <span> · Se cancelará al publicar</span>}
              {tasksShared && !state.draft && (
                <>
                  {' '}
                  <span>{STATUS_LABELS[template.status]}</span>
                  {template.status === 'BLOQUEADA' && template.blockedReason !== null && (
                    <span> · {template.blockedReason}</span>
                  )}
                </>
              )}
              {!template.cancelled && (
                <button type="button" onClick={() => onCancel(template.id)}>
                  Marcar para cancelar
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
          <label htmlFor={ids.title}>Título de la plantilla</label>
          <input
            id={ids.title}
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <label htmlFor={ids.kind}>Tipo</label>
          <select
            id={ids.kind}
            value={kind}
            onChange={(event) => setKind(event.target.value as 'SALUD' | 'NAVE')}
          >
            <option value="SALUD">Salud</option>
            <option value="NAVE">Nave</option>
          </select>
          <button type="submit" disabled={title.trim() === ''}>
            Añadir plantilla
          </button>
        </form>

        <button type="button" disabled={!hasChanges(state)} onClick={onPublish}>
          {state.draft ? `Publicar plan v${state.draft.version}` : 'Publicar plan'}
        </button>
      </section>

      {published && (
        <section aria-label="Estado del plan">
          <ol aria-label={`Estado del plan v${published.version}`}>
            {STAGES.map(({ stage, label }) => {
              const reached = STAGES.findIndex((s) => s.stage === published.stage)
              const index = STAGES.findIndex((s) => s.stage === stage)
              const isCurrent =
                stage === published.stage || (published.stage === 'EN_COLA' && stage === 'PUBLICADO')
              return (
                <li
                  key={stage}
                  aria-current={isCurrent ? 'step' : undefined}
                  data-reached={published.stage === 'EN_COLA' ? index === 0 : index <= reached}
                >
                  {label}
                </li>
              )
            })}
          </ol>
          {published.stage === 'EN_COLA' && (
            <p>En cola: sin enlace con la nave. El plan llegará cuando se restablezca.</p>
          )}
        </section>
      )}
    </main>
  )
}
