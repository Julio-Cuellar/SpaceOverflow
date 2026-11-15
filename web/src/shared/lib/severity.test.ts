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
    expect(severityMeta('ATENCION').symbol).toBe('▲')
    expect(severityMeta('CRITICO').symbol).toBe('■')
  })
})

describe('worstSeverity', () => {
  it('returns the most severe level of a list', () => {
    expect(worstSeverity(['NORMAL', 'CRITICO', 'ATENCION'])).toBe('CRITICO')
  })

  it('ranks ALERTA between ATENCION and CRITICO', () => {
    expect(worstSeverity(['ATENCION', 'ALERTA'])).toBe('ALERTA')
    expect(worstSeverity(['ALERTA', 'CRITICO'])).toBe('CRITICO')
  })

  it('returns NORMAL for an empty list', () => {
    expect(worstSeverity([])).toBe('NORMAL')
  })
})
