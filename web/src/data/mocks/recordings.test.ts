import { describe, expect, it } from 'vitest'
import { normalRecording } from './ws/recordings'

describe('grabación WS de ejemplo', () => {
  it('includes telemetry ticks, so the replayer can drive the cabin panel at 1 Hz', () => {
    expect(normalRecording.some((m) => m.type === 'telemetry.tick')).toBe(true)
  })

  it('every message has the shape of the /ws envelope', () => {
    for (const m of normalRecording) {
      expect(m).toEqual(
        expect.objectContaining({
          topic: expect.any(String),
          type: expect.any(String),
          at: expect.any(String),
        }),
      )
      expect(m.seq === null || typeof m.seq === 'number').toBe(true)
    }
  })
})
