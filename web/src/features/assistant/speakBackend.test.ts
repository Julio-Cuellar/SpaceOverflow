import { describe, expect, it, vi } from 'vitest'
import { speakBackend } from './speakBackend'

const wav = () => new Response(new Blob(['RIFFfake'], { type: 'audio/wav' }), { status: 200 })

describe('speakBackend', () => {
  it('sends the answer to the voice route and plays the audio it gets back', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(wav())
    const play = vi.fn().mockResolvedValue(undefined)

    await speakBackend('/api/v1/voice/speak', fetchImpl, play)('The limit is 3 mmHg.')

    expect(fetchImpl).toHaveBeenCalledWith(
      '/api/v1/voice/speak',
      expect.objectContaining({
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text: 'The limit is 3 mmHg.' }),
      }),
    )
    expect(play).toHaveBeenCalledTimes(1)
    expect(play.mock.calls[0][0]).toBeInstanceOf(Blob)
  })

  it('fails instead of staying silent when the voice service is not available', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response('{}', { status: 503 }))
    const play = vi.fn()

    await expect(speakBackend('/v', fetchImpl, play)('hello')).rejects.toThrow(/503/)
    expect(play).not.toHaveBeenCalled()
  })

  it('does not play an empty reply', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response('', { status: 200 }))
    const play = vi.fn()

    await expect(speakBackend('/v', fetchImpl, play)('hello')).rejects.toThrow()
    expect(play).not.toHaveBeenCalled()
  })

  it('passes along a playback failure', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(wav())
    const play = vi.fn().mockRejectedValue(new Error('NotAllowedError'))

    await expect(speakBackend('/v', fetchImpl, play)('hello')).rejects.toThrow('NotAllowedError')
  })
})
