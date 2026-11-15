import type { WsMessage } from './types'

export interface StreamOptions {
  /** Tope de mensajes pendientes antes de descartar ticks. Las alertas nunca se descartan. */
  maxPending?: number
}

export interface Stream {
  /** Devuelve false si el mensaje ya se aplicó o es más viejo que el último seq. */
  push: (message: WsMessage) => boolean
  /** Entrega los pendientes en orden de llegada y vacía la cola. */
  drain: () => WsMessage[]
  /** Último seq aplicado. Se envía en `resume` al reconectar. */
  lastSeq: () => number
}

const tickKey = (message: WsMessage): string => {
  const data = message.data as { zone_id?: string; metric?: string }
  return `${data.zone_id ?? ''}:${data.metric ?? ''}`
}

/** Cola de un cliente: deduplica por seq, coalesce ticks y descarta ticks antes que alertas. */
export function createStream(options: StreamOptions = {}): Stream {
  const maxPending = options.maxPending ?? 500
  let pending: WsMessage[] = []
  let lastSeq = 0

  const dropOldestTick = (): boolean => {
    const index = pending.findIndex((m) => m.type === 'telemetry.tick')
    if (index === -1) return false
    pending.splice(index, 1)
    return true
  }

  return {
    push: (message) => {
      if (message.seq !== null) {
        if (message.seq <= lastSeq) return false
        lastSeq = message.seq
        pending.push(message)
      } else {
        // Un tick reemplaza al anterior de la misma zona y métrica: solo importa el último valor.
        const key = tickKey(message)
        pending = pending.filter((m) => !(m.type === 'telemetry.tick' && tickKey(m) === key))
        pending.push(message)
      }

      while (pending.length > maxPending && dropOldestTick()) {
        // Se descartan ticks hasta volver al tope. Si no quedan ticks, las alertas se conservan.
      }
      return true
    },
    drain: () => {
      const out = pending
      pending = []
      return out
    },
    lastSeq: () => lastSeq,
  }
}
