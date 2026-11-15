import type { BodyIndicator } from '../../features/cabin/BodyMap'

/**
 * Seis indicadores del cuerpo (plan, sección 13.6). Son valores de demostración y se muestran
 * como simulados; el backend los reemplazará cuando exista la telemetría real.
 */
export const bodyIndicatorsFixture: BodyIndicator[] = [
  { key: 'cabeza', label: 'Cabeza', value: 'Ánimo estable, sin cefalea', severity: 'NORMAL', hazard: 'entorno', evidenceState: 'DEMO' },
  { key: 'pulmones', label: 'Pulmones', value: 'SpO₂ 98 %', severity: 'NORMAL', hazard: 'entorno', evidenceState: 'DEMO' },
  { key: 'corazon', label: 'Corazón', value: '72 lpm', severity: 'NORMAL', hazard: 'gravedad', evidenceState: 'DEMO' },
  { key: 'sangre', label: 'Sangre y órganos', value: 'Radiación acumulada baja', severity: 'NORMAL', hazard: 'radiacion', evidenceState: 'DEMO' },
  { key: 'temperatura', label: 'Temperatura', value: '36.6 °C', severity: 'NORMAL', hazard: 'entorno', evidenceState: 'DEMO' },
  { key: 'huesos', label: 'Huesos y músculo', value: 'Línea base al 95 %', severity: 'NORMAL', hazard: 'gravedad', evidenceState: 'DEMO' },
]
