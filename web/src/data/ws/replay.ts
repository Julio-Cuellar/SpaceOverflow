import type { WsMessage } from './types'

export interface ReplayOptions {
  intervalMs: number
  loop?: boolean
}

export interface Replayer {
  start: () => void
  stop: () => void
}

/** Emite mensajes grabados uno por intervalo, como si llegaran por el WebSocket. */
export function createReplayer(
  messages: readonly WsMessage[],
  emit: (message: WsMessage) => void,
  options: ReplayOptions,
): Replayer {
  let timer: ReturnType<typeof setInterval> | undefined
  let index = 0

  const stop = () => {
    if (timer !== undefined) {
      clearInterval(timer)
      timer = undefined
    }
  }

  const tick = () => {
    if (index >= messages.length) {
      if (!options.loop || messages.length === 0) {
        stop()
        return
      }
      index = 0
    }
    emit(messages[index])
    index += 1
  }

  return {
    start: () => {
      if (timer !== undefined) return
      index = 0
      timer = setInterval(tick, options.intervalMs)
    },
    stop,
  }
}
