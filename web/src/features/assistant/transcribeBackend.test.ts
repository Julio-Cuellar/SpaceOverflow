import { describe, expect, it, vi } from 'vitest'
import { transcribeBackend } from './transcribeBackend'

const json = (payload: unknown, status = 200) =>
  new Response(JSON.stringify(payload), { status })

const state = (status: string, text = '', reasonCode: string | null = null) => ({
  utterance_id: 'u-1',
  status,
  text,
  confidence: null,
  reason: null,
  reason_code: reasonCode,
})

const audio = new Blob(['bytes'], { type: 'audio/webm;codecs=opus' })

describe('transcribeBackend', () => {
  it('uploads the recording and returns the text once it is transcribed', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(json({ utterance_id: 'u-1' }, 202))
      .mockResolvedValueOnce(json(state('TRANSCRIBED', 'what is the cabin pressure')))

    const result = await transcribeBackend('/api/v1/voice/utterances', 'conv-1', fetchImpl, 0)(audio)

    expect(result).toEqual({ text: 'what is the cabin pressure' })
    const [url, init] = fetchImpl.mock.calls[0]
    expect(url).toBe('/api/v1/voice/utterances?conversation_id=conv-1')
    expect(init.method).toBe('POST')
    expect(init.headers['content-type']).toBe('audio/webm;codecs=opus')
    expect(init.body).toBe(audio)
    expect(fetchImpl.mock.calls[1][0]).toBe('/api/v1/voice/utterances/u-1')
  })

  it('keeps asking while the backend is still transcribing', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(json({ utterance_id: 'u-1' }, 202))
      .mockResolvedValueOnce(json(state('RECEIVED')))
      .mockResolvedValueOnce(json(state('TRANSCRIBING')))
      .mockResolvedValueOnce(json(state('TRANSCRIBED', 'hello')))

    const result = await transcribeBackend('/v', 'c', fetchImpl, 0)(audio)

    expect(result).toEqual({ text: 'hello' })
    expect(fetchImpl).toHaveBeenCalledTimes(4)
  })

  it('returns null only when nothing was heard', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(json({ utterance_id: 'u-1' }, 202))
      .mockResolvedValueOnce(json(state('NO_TRANSCRIPT', '', 'NO_SPEECH')))

    expect(await transcribeBackend('/v', 'c', fetchImpl, 0)(audio)).toBeNull()
  })

  it.each(['FAILED', 'NO_MODEL'])(
    'fails, instead of saying nothing was heard, when the voice service reports %s',
    async (code) => {
      const fetchImpl = vi
        .fn()
        .mockResolvedValueOnce(json({ utterance_id: 'u-1' }, 202))
        .mockResolvedValueOnce(json(state('NO_TRANSCRIPT', '', code)))

      await expect(transcribeBackend('/v', 'c', fetchImpl, 0)(audio)).rejects.toThrow(code)
    },
  )

  it('fails instead of inventing a transcript when the upload is refused', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(json({ detail: 'nope' }, 415))

    await expect(transcribeBackend('/v', 'c', fetchImpl, 0)(audio)).rejects.toThrow()
  })

  it('fails when the status request fails', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(json({ utterance_id: 'u-1' }, 202))
      .mockResolvedValueOnce(json({ detail: 'boom' }, 500))

    await expect(transcribeBackend('/v', 'c', fetchImpl, 0)(audio)).rejects.toThrow()
  })

  it('gives up when the transcription never finishes', async () => {
    const fetchImpl = vi.fn().mockImplementation((url: string) =>
      Promise.resolve(url.includes('conversation_id') ? json({ utterance_id: 'u-1' }, 202) : json(state('TRANSCRIBING'))),
    )

    await expect(transcribeBackend('/v', 'c', fetchImpl, 0, 3)(audio)).rejects.toThrow(/too long/i)
  })
})
