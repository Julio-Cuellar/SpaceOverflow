import { describe, expect, it, vi } from 'vitest'
import { askBackend } from './askBackend'

const body = {
  state: 'ANSWERED',
  outcome: 'ANSWERED',
  text: 'El límite es 3 mmHg.',
  composed_by: 'n8n',
  degraded: false,
  citations: [
    {
      document_code: 'OCHMO-TB-004 CO₂',
      requirement_ref: 'V2 6004',
      page: 16,
      excerpt: 'no more than 3 mmHg',
      evidence_state: 'TB',
    },
  ],
}

const respond = (payload: unknown, init: ResponseInit = { status: 200 }) =>
  vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), init))

describe('askBackend', () => {
  it('sends the question to the backend and maps the answer with its citations', async () => {
    const fetchImpl = respond(body)

    const answer = await askBackend('/dev/ask', fetchImpl)('What is the CO2 limit?')

    expect(fetchImpl).toHaveBeenCalledWith(
      '/dev/ask',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ text: 'What is the CO2 limit?' }),
      }),
    )
    expect(answer.outcome).toBe('ANSWERED')
    expect(answer.text).toBe('El límite es 3 mmHg.')
    expect(answer.citations).toEqual([
      {
        documentCode: 'OCHMO-TB-004 CO₂',
        requirementRef: 'V2 6004',
        excerpt: 'no more than 3 mmHg',
        evidenceState: 'TB',
      },
    ])
  })

  it('keeps the no-information outcome the backend decided', async () => {
    const fetchImpl = respond({ ...body, outcome: 'NO_INFO', text: "I don't have that information.", citations: [] })

    const answer = await askBackend('/dev/ask', fetchImpl)('¿Capital de Francia?')

    expect(answer.outcome).toBe('NO_INFO')
    expect(answer.citations).toEqual([])
  })

  it('fails instead of inventing an answer when the backend does not respond well', async () => {
    const failing = respond({ detail: 'boom' }, { status: 500 })
    await expect(askBackend('/dev/ask', failing)('pregunta')).rejects.toThrow()

    const unreachable = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(askBackend('/dev/ask', unreachable)('pregunta')).rejects.toThrow()
  })

  it('rejects an evidence state the interface does not know', async () => {
    const odd = respond({ ...body, citations: [{ ...body.citations[0], evidence_state: 'INVENTADO' }] })

    await expect(askBackend('/dev/ask', odd)('pregunta')).rejects.toThrow()
  })
})
