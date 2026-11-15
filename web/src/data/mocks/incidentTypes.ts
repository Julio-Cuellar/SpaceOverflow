import type { EvidenceState } from '../../shared/lib/evidence'
import type { Severity } from '../../shared/lib/severity'

export interface IncidentTypeView {
  key: string
  category: string
  name: string
  /** AUTO: lo detecta una regla. MANUAL: lo reporta la tripulación. */
  detection: 'AUTO' | 'MANUAL'
  defaultSeverity: Severity
  evidenceState: EvidenceState
  typicalZones: string[]
  suggestedActions: string[]
}

/**
 * Muestra de 6 de los 61 tipos del catálogo (plan, sección 13.9).
 * El catálogo completo llega como dato versionado; aquí solo sirve para la interfaz.
 */
export const incidentTypesFixture: IncidentTypeView[] = [
  {
    key: 'co2_high',
    category: 'Atmósfera y soporte vital',
    name: 'CO₂ alto',
    detection: 'AUTO',
    defaultSeverity: 'ALERTA',
    evidenceState: 'VERIFICADO',
    typicalZones: ['Cualquiera'],
    suggestedActions: ['Revisar ventilación y filtros de CO₂', 'Medir CO₂ en zonas locales'],
  },
  {
    key: 'hypoxia',
    category: 'Atmósfera y soporte vital',
    name: 'Hipoxia (PIO₂ baja)',
    detection: 'AUTO',
    defaultSeverity: 'CRITICO',
    evidenceState: 'VERIFICADO',
    typicalZones: ['Soporte vital', 'Cualquiera'],
    suggestedActions: ['Revisar suministro de O₂ y presión', 'Reducir el esfuerzo físico'],
  },
  {
    key: 'smoke_fire',
    category: 'Fuego y humo',
    name: 'Humo o incendio',
    detection: 'AUTO',
    defaultSeverity: 'CRITICO',
    evidenceState: 'DEMO',
    typicalZones: ['Cocina y comedor', 'Ingeniería y propulsión', 'Almacén'],
    suggestedActions: ['Activar el procedimiento de incendio', 'Aislar la zona'],
  },
  {
    key: 'burning_smell',
    category: 'Fuego y humo',
    name: 'Olor a quemado o sobrecalentamiento',
    detection: 'MANUAL',
    defaultSeverity: 'ALERTA',
    evidenceState: 'DEMO',
    typicalZones: ['Cualquiera'],
    suggestedActions: ['Desconectar el equipo sospechoso', 'Inspeccionar la zona'],
  },
  {
    key: 'injury',
    category: 'Salud de la tripulación',
    name: 'Lesión o accidente',
    detection: 'MANUAL',
    defaultSeverity: 'ALERTA',
    evidenceState: 'DEMO',
    typicalZones: ['Cualquiera'],
    suggestedActions: ['Atender y avisar al oficial médico (CMO)'],
  },
  {
    key: 'loose_cargo',
    category: 'Carga, equipo y ciencia',
    name: 'Carga mal sujeta o herramienta perdida',
    detection: 'MANUAL',
    defaultSeverity: 'ATENCION',
    evidenceState: 'DEMO',
    typicalZones: ['Almacén'],
    suggestedActions: ['Asegurar la carga y registrar el inventario'],
  },
]
