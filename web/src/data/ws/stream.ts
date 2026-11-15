import type { WsMessage } from './types'

export interface StreamOptions {
  /** Cap on pending messages before ticks are dropped. Alerts are never dropped. */
  maxPending?: number
}

export interface Stream {
  /** Returns false if the message was already applied or is older than the last seq. */
  push: (message: WsMessage) => boolean
  /** Delivers the pending messages in order of arrival and empties the queue. */
  drain: () => WsMessage[]
  /** Last applied seq. Sent in `resume` on reconnection. */
  lastSeq: () => number
}

const tickKey = (message: WsMessage): string => {
  const data = message.data as { zone_id?: string; metric?: string }
  return `${data.zone_id ?? ''}:${data.metric ?? ''}`
}

/** A client queue: deduplicates by seq, coalesces ticks and drops ticks before alerts. */
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
        // A tick replaces the previous one of the same zone and metric: only the last value matters.
        const key = tickKey(message)
        pending = pending.filter((m) => !(m.type === 'telemetry.tick' && tickKey(m) === key))
        pending.push(message)
      }

      while (pending.length > maxPending && dropOldestTick()) {
        // Ticks are dropped until the queue is back under the cap. If no ticks remain, alerts are kept.
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
