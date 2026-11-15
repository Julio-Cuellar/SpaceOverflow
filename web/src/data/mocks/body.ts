import type { BodyIndicator } from '../../features/cabin/BodyMap'

/**
 * Six body indicators (architecture plan, section 13.6). They are demo values and are shown
 * as simulated; the backend will replace them once real telemetry exists.
 */
export const bodyIndicatorsFixture: BodyIndicator[] = [
  { key: 'head', label: 'Head', value: 'Stable mood, no headache', severity: 'NORMAL', hazard: 'environment', evidenceState: 'DEMO' },
  { key: 'lungs', label: 'Lungs', value: 'SpO₂ 98 %', severity: 'NORMAL', hazard: 'environment', evidenceState: 'DEMO' },
  { key: 'heart', label: 'Heart', value: '72 bpm', severity: 'NORMAL', hazard: 'gravity', evidenceState: 'DEMO' },
  { key: 'blood', label: 'Blood and organs', value: 'Low accumulated radiation', severity: 'NORMAL', hazard: 'radiation', evidenceState: 'DEMO' },
  { key: 'temperature', label: 'Temperature', value: '36.6 °C', severity: 'NORMAL', hazard: 'environment', evidenceState: 'DEMO' },
  { key: 'bones', label: 'Bones and muscle', value: 'Baseline at 95 %', severity: 'NORMAL', hazard: 'gravity', evidenceState: 'DEMO' },
]
