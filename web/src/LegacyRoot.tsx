import { useEffect, useRef, useState } from 'react'
import { App, type AppProps } from './App'
import {
  addTemplate,
  advancePlan,
  initialGroundState,
  markForCancel,
  publishPlan,
  setLink,
} from './features/ground/model'
import { GroundPanel } from './features/ground/GroundPanel'

const GROUND_PATH = '/ground'
const INITIAL_VERSION = initialGroundState().version

/**
 * Elige entre la nave y el panel de Tierra (la misma SPA con rol `ground`, plan 11.1). En esta
 * demo los dos comparten el estado del plan en memoria; con el backend (I7) cada uno hablará con
 * el suyo por el enlace.
 */
export function LegacyRoot({
  initialPath = window.location.pathname,
  askAssistant,
  transcribeVoice,
  speak,
}: {
  initialPath?: string
  askAssistant?: AppProps['askAssistant']
  transcribeVoice?: AppProps['transcribeVoice']
  speak?: AppProps['speak']
}) {
  const [path, setPath] = useState(initialPath)
  const [ground, setGround] = useState(initialGroundState)
  const [tasksShared, setTasksShared] = useState(true)
  const templateCount = useRef(0)

  const inFlight = ground.published !== null && !['CONFIRMADO', 'EN_COLA'].includes(ground.published.stage)
  const delayMs = ground.link.delaySeconds * 1000
  useEffect(() => {
    if (!inFlight) return
    const timer = setInterval(() => setGround(advancePlan), delayMs)
    return () => clearInterval(timer)
  }, [inFlight, delayMs])

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const go = (target: string) => (event: React.MouseEvent) => {
    event.preventDefault()
    window.history.pushState(null, '', target)
    setPath(target)
  }

  if (path === GROUND_PATH) {
    return (
      <>
        <p>
          <a href="/" onClick={go('/')}>
            Ir a la nave
          </a>
        </p>
        <GroundPanel
          state={ground}
          tasksShared={tasksShared}
          onAddTemplate={(template) => {
            templateCount.current += 1
            const id = `tpl-demo-${templateCount.current}`
            setGround((g) => addTemplate(g, template, id))
          }}
          onCancel={(id) => setGround((g) => markForCancel(g, id))}
          onPublish={() => setGround(publishPlan)}
          onLink={(change) => setGround((g) => setLink(g, change))}
        />
      </>
    )
  }

  return (
    <>
      <p>
        <a href={GROUND_PATH} onClick={go(GROUND_PATH)}>
          Panel de Tierra
        </a>
      </p>
      <App
        planNotice={ground.version > INITIAL_VERSION ? `Plan v${ground.version} aplicado` : undefined}
        tasksShared={tasksShared}
        onTasksSharedChange={setTasksShared}
        askAssistant={askAssistant}
        transcribeVoice={transcribeVoice}
        speak={speak}
      />
    </>
  )
}
