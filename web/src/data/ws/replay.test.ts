import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createReplayer } from './replay'
import type { WsMessage } from './types'

const message = (seq: number | null, type: string): WsMessage => ({
  seq,
  topic: 'telemetry',
  type,
  at: '2026-11-14T00:00:00Z',
  data: {},
})

describe('createReplayer', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('emits nothing before start()', () => {
    const emitted: string[] = []
    createReplayer([message(null, 'telemetry.tick')], (m) => emitted.push(m.type), {
      intervalMs: 1000,
    })

    vi.advanceTimersByTime(5000)

    expect(emitted).toEqual([])
  })

  it('emits the recorded messages in order, one every interval (1 Hz for ticks)', () => {
    const emitted: string[] = []
    const replayer = createReplayer(
      [message(null, 'telemetry.tick'), message(1, 'alert.raised')],
      (m) => emitted.push(m.type),
      { intervalMs: 1000 },
    )

    replayer.start()
    vi.advanceTimersByTime(999)
    expect(emitted).toEqual([])

    vi.advanceTimersByTime(1)
    expect(emitted).toEqual(['telemetry.tick'])

    vi.advanceTimersByTime(1000)
    expect(emitted).toEqual(['telemetry.tick', 'alert.raised'])
  })

  it('stops emitting after stop()', () => {
    const emitted: string[] = []
    const replayer = createReplayer(
      [message(null, 'telemetry.tick'), message(null, 'telemetry.tick')],
      (m) => emitted.push(m.type),
      { intervalMs: 1000 },
    )

    replayer.start()
    vi.advanceTimersByTime(1000)
    replayer.stop()
    vi.advanceTimersByTime(5000)

    expect(emitted).toHaveLength(1)
  })

  it('starts again from the beginning when loop is true', () => {
    const emitted: string[] = []
    const replayer = createReplayer([message(null, 'telemetry.tick')], (m) => emitted.push(m.type), {
      intervalMs: 1000,
      loop: true,
    })

    replayer.start()
    vi.advanceTimersByTime(3000)

    expect(emitted).toEqual(['telemetry.tick', 'telemetry.tick', 'telemetry.tick'])
  })

  it('emits nothing and stops when the recording is empty, even in loop mode', () => {
    const emitted: string[] = []
    const replayer = createReplayer([], (m) => emitted.push(m.type), {
      intervalMs: 1000,
      loop: true,
    })

    replayer.start()
    vi.advanceTimersByTime(3000)

    expect(emitted).toEqual([])
  })

  it('does not start a second timer when start() is called twice', () => {
    const emitted: string[] = []
    const replayer = createReplayer([message(null, 'telemetry.tick')], (m) => emitted.push(m.type), {
      intervalMs: 1000,
    })

    replayer.start()
    replayer.start()
    vi.advanceTimersByTime(1000)

    expect(emitted).toEqual(['telemetry.tick'])
  })
})
