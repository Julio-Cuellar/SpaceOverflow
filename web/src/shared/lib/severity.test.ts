import { describe, expect, it } from 'vitest'
import { SEVERITIES, severityMeta, worstSeverity } from './severity'

describe('severityMeta', () => {
  it('pairs every level with a distinct symbol and a non-empty text label', () => {
    const symbols = SEVERITIES.map((s) => severityMeta(s).symbol)
    const labels = SEVERITIES.map((s) => severityMeta(s).label)

    expect(new Set(symbols).size).toBe(SEVERITIES.length)
    expect(labels.every((label) => label.length > 0)).toBe(true)
  })

  it('uses the symbols of the project spec for normal, attention and critical', () => {
    expect(severityMeta('NORMAL').symbol).toBe('●')
    expect(severityMeta('ATTENTION').symbol).toBe('▲')
    expect(severityMeta('CRITICAL').symbol).toBe('■')
  })
})

describe('worstSeverity', () => {
  it('returns the most severe level of a list', () => {
    expect(worstSeverity(['NORMAL', 'CRITICAL', 'ATTENTION'])).toBe('CRITICAL')
  })

  it('ranks ALERT between ATTENTION and CRITICAL', () => {
    expect(worstSeverity(['ATTENTION', 'ALERT'])).toBe('ALERT')
    expect(worstSeverity(['ALERT', 'CRITICAL'])).toBe('CRITICAL')
  })

  it('returns NORMAL for an empty list', () => {
    expect(worstSeverity([])).toBe('NORMAL')
  })
})
