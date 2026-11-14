import type { EvidenceState } from '../../shared/lib/evidence'
import { type Severity, worstSeverity } from '../../shared/lib/severity'

export type Scenario = 'normal' | 'co2-alto'

export interface Vital {
  key: string
  label: string
  value: number
  unit: string
  domain: 'cabina' | 'cuerpo'
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
 * Datos de ejemplo para la interfaz sin backend (fase F0, hasta el hito I2).
 * Los valores son ilustrativos; la interfaz muestra lo que calcula el backend.
 */
export function dashboardFixture(scenario: Scenario): DashboardView {
  const highCo2 = scenario === 'co2-alto'

  const vitals: Vital[] = [
    {
      key: 'ppco2_1h',
      label: 'CO₂ promedio de 1 h',
      value: highCo2 ? 3.4 : 1.2,
      unit: 'mmHg',
      domain: 'cabina',
      severity: highCo2 ? 'ALERTA' : 'NORMAL',
      evidenceState: 'VERIFICADO',
      origin: 'SIMULATED',
    },
    {
      key: 'pio2',
      label: 'PIO₂',
      value: 149.7,
      unit: 'mmHg',
      domain: 'cabina',
      severity: 'NORMAL',
      evidenceState: 'VERIFICADO',
      origin: 'SIMULATED',
    },
    {
      key: 'humedad',
      label: 'Humedad relativa',
      value: 45,
      unit: '%',
      domain: 'cabina',
      severity: 'NORMAL',
      evidenceState: 'DEMO',
      origin: 'SIMULATED',
    },
    {
      key: 'frecuencia_cardiaca',
      label: 'Frecuencia cardíaca',
      value: 72,
      unit: 'lpm',
      domain: 'cuerpo',
      severity: 'NORMAL',
      evidenceState: 'DEMO',
      origin: 'SIMULATED',
    },
    {
      key: 'spo2',
      label: 'SpO₂',
      value: 98,
      unit: '%',
      domain: 'cuerpo',
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
