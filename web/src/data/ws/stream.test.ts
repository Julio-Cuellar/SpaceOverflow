import { describe, expect, it } from 'vitest'
import { createStream } from './stream'
import type { WsMessage } from './types'

const event = (seq: number, type: string): WsMessage => ({
  seq,
  topic: 'alerts',
  type,
  at: '2026-11-14T10:00:00Z',
  data: { seq },
})

const tick = (zone: string, metric: string, value: number): WsMessage => ({
  seq: null,
  topic: 'telemetry',
  type: 'telemetry.tick',
  at: '2026-11-14T10:00:00Z',
  data: { zone_id: zone, metric, value },
})

describe('createStream', () => {
  it('applies a message once even if it arrives twice', () => {
    const stream = createStream()

    stream.push(event(5, 'alert.raised'))
    stream.push(event(5, 'alert.raised'))

    expect(stream.drain()).toHaveLength(1)
  })

  it('ignores events older than the last seq it has applied', () => {
    const stream = createStream()

    stream.push(event(5, 'alert.raised'))
    stream.push(event(3, 'alert.raised'))

    expect(stream.drain().map((m) => m.seq)).toEqual([5])
  })

  it('coalesces telemetry ticks to the latest value per zone and metric', () => {
    const stream = createStream()

    stream.push(tick('cabina', 'ppco2_1h', 1.1))
    stream.push(tick('cabina', 'ppco2_1h', 1.4))

    const drained = stream.drain()
    expect(drained).toHaveLength(1)
    expect(drained[0].data).toEqual({ zone_id: 'cabina', metric: 'ppco2_1h', value: 1.4 })
  })

  it('drops telemetry ticks first under pressure, and never drops alerts', () => {
    const stream = createStream({ maxPending: 2 })

    stream.push(tick('cabina', 'pio2', 150))
    stream.push(event(7, 'alert.raised'))
    stream.push(tick('cabina', 'ppco2_1h', 1.2))

    const types = stream.drain().map((m) => m.type)
    expect(types).toContain('alert.raised')
    expect(types.filter((t) => t === 'telemetry.tick')).toHaveLength(1)
  })

  it('keeps every alert even when the queue is full of alerts', () => {
    const stream = createStream({ maxPending: 2 })

    stream.push(event(1, 'alert.raised'))
    stream.push(event(2, 'alert.raised'))
    stream.push(event(3, 'alert.resolved'))

    expect(stream.drain().map((m) => m.seq)).toEqual([1, 2, 3])
  })

  it('exposes the last applied seq, for the resume message after a reconnection', () => {
    const stream = createStream()

    stream.push(event(9, 'alert.raised'))

    expect(stream.lastSeq()).toBe(9)
  })
})
