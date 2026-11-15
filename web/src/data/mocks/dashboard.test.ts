import { describe, expect, it } from 'vitest'
import { dashboardFixture } from './fixtures'

describe('dashboardFixture', () => {
  it('returns a normal dashboard where every vital states its evidence', () => {
    const dashboard = dashboardFixture('normal')

    expect(dashboard.globalSeverity).toBe('NORMAL')
    expect(dashboard.vitals.length).toBeGreaterThan(0)
    expect(dashboard.vitals.every((v) => v.evidenceState)).toBe(true)
  })

  it('raises the global severity to red (ALERTA) in the high CO2 scenario', () => {
    expect(dashboardFixture('co2-alto').globalSeverity).toBe('ALERTA')
  })

  it('marks body values as simulated, so the interface can say so', () => {
    const bodyValues = dashboardFixture('normal').vitals.filter((v) => v.domain === 'cuerpo')

    expect(bodyValues.length).toBeGreaterThan(0)
    expect(bodyValues.every((v) => v.origin === 'SIMULATED')).toBe(true)
  })
})
