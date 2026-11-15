import type { EvidenceState } from '../../shared/lib/evidence'
import { type Severity, worstSeverity } from '../../shared/lib/severity'

export type Scenario = 'normal' | 'co2_slow'

export interface Vital {
  key: string
  label: string
  value: number
  unit: string
  domain: 'cabin' | 'body'
  severity: Severity
  evidenceState: EvidenceState
  origin: 'REAL' | 'SIMULATED' | 'REPLAY'
}

export interface DashboardView {
  habitatId: string
  globalSeverity: Severity
  vitals: Vital[]
}

/**
 * Example data for the interface without a backend (phase F0, until milestone I2).
 * The values are illustrative; the interface shows what the backend computes.
 */
export function dashboardFixture(scenario: Scenario): DashboardView {
  const highCo2 = scenario === 'co2_slow'

  const vitals: Vital[] = [
    {
      key: 'ppco2_1h',
      label: '1 h average CO₂',
      value: highCo2 ? 3.4 : 1.2,
      unit: 'mmHg',
      domain: 'cabin',
      severity: highCo2 ? 'ALERT' : 'NORMAL',
      evidenceState: 'VERIFIED',
      origin: 'SIMULATED',
    },
    {
      key: 'pio2',
      label: 'PIO₂',
      value: 149.7,
      unit: 'mmHg',
      domain: 'cabin',
      severity: 'NORMAL',
      evidenceState: 'VERIFIED',
      origin: 'SIMULATED',
    },
    {
      key: 'humidity',
      label: 'Relative humidity',
      value: 45,
      unit: '%',
      domain: 'cabin',
      severity: 'NORMAL',
      evidenceState: 'DEMO',
      origin: 'SIMULATED',
    },
    {
      key: 'heart_rate',
      label: 'Heart rate',
      value: 72,
      unit: 'bpm',
      domain: 'body',
      severity: 'NORMAL',
      evidenceState: 'DEMO',
      origin: 'SIMULATED',
    },
    {
      key: 'spo2',
      label: 'SpO₂',
      value: 98,
      unit: '%',
      domain: 'body',
      severity: 'NORMAL',
      evidenceState: 'DEMO',
      origin: 'SIMULATED',
    },
  ]

  return {
    habitatId: 'hab-01',
    globalSeverity: worstSeverity(vitals.map((v) => v.severity)),
    vitals,
  }
}
