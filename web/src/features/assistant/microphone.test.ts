import { afterEach, describe, expect, it, vi } from 'vitest'
import { microphoneAvailable, startMicrophoneRecording } from './microphone'

class FakeRecorder {
  static last: FakeRecorder | undefined
  state: 'inactive' | 'recording' = 'inactive'
  ondataavailable: ((event: { data: Blob }) => void) | null = null
  onstop: (() => void) | null = null
  constructor(readonly stream: unknown) {
    FakeRecorder.last = this
  }
  start() {
    this.state = 'recording'
  }
  stop() {
    this.state = 'inactive'
    this.ondataavailable?.({ data: new Blob(['chunk-1']) })
    this.ondataavailable?.({ data: new Blob(['chunk-2']) })
    this.onstop?.()
  }
}

const track = { stop: vi.fn() }
const stream = { getTracks: () => [track] }

afterEach(() => {
  vi.unstubAllGlobals()
  track.stop.mockClear()
})

describe('microphone', () => {
  it('is not available without mediaDevices (insecure context or no hardware)', () => {
    vi.stubGlobal('navigator', {})

    expect(microphoneAvailable()).toBe(false)
  })

  it('is available when the browser offers getUserMedia and MediaRecorder', () => {
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia: vi.fn() } })
    vi.stubGlobal('MediaRecorder', FakeRecorder)

    expect(microphoneAvailable()).toBe(true)
  })

  it('records until stopped, joins the chunks into one blob and releases the microphone', async () => {
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia: vi.fn(async () => stream) } })
    vi.stubGlobal('MediaRecorder', FakeRecorder)

    const recording = await startMicrophoneRecording()
    expect(FakeRecorder.last?.state).toBe('recording')
    const blob = await recording.stop()

    expect(blob.size).toBe('chunk-1chunk-2'.length)
    expect(track.stop).toHaveBeenCalledTimes(1)
  })

  it('rejects when the crew denies the permission', async () => {
    vi.stubGlobal('navigator', {
      mediaDevices: {
        getUserMedia: vi.fn(async () => {
          throw new Error('NotAllowedError')
        }),
      },
    })
    vi.stubGlobal('MediaRecorder', FakeRecorder)

    await expect(startMicrophoneRecording()).rejects.toThrow('NotAllowedError')
  })

  it('rejects when there is no microphone support at all', async () => {
    vi.stubGlobal('navigator', {})

    await expect(startMicrophoneRecording()).rejects.toThrow(/micrófono/)
  })
})
