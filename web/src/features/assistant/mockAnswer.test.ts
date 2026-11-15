import { describe, expect, it } from 'vitest'
import { mockAnswer } from './mockAnswer'

describe('mockAnswer', () => {
  it('answers a headache question with the TB-004 passage and its citation', () => {
    const answer = mockAnswer('Why do I have a headache?', [])

    expect(answer.outcome).toBe('ANSWERED')
    expect(answer.text.toLowerCase()).toContain('headache between 2.8 and 4.5 mmhg')
    expect(answer.citations[0]).toEqual(
      expect.objectContaining({ documentCode: 'OCHMO-TB-004 CO₂', evidenceState: 'TB' }),
    )
  })

  it('says it has no information when no passage is relevant, and cites nothing', () => {
    const answer = mockAnswer('How do I change the airlock filter?', [])

    expect(answer.outcome).toBe('NO_INFO')
    expect(answer.text).toBe("I don't have that information in the loaded sources.")
    expect(answer.citations).toEqual([])
  })

  it('names the active alert without changing it', () => {
    const answer = mockAnswer('Why do I have a headache?', ['CO₂ alto (Alerta)'])

    expect(answer.text).toContain('According to the loaded sources:')
    expect(answer.text).toContain('Active alert: CO₂ alto (Alerta)')
    expect(answer.text).toContain('does not change the alert')
  })
})
