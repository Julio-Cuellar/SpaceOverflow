import type { EvidenceState } from '../../shared/lib/evidence'
import type { Severity } from '../../shared/lib/severity'

export interface IncidentTypeView {
  key: string
  category: string
  name: string
  /** AUTO: detected by a rule. MANUAL: reported by the crew. */
  detection: 'AUTO' | 'MANUAL'
  defaultSeverity: Severity
  evidenceState: EvidenceState
  typicalZones: string[]
  suggestedActions: string[]
}

/**
 * Sample of 6 of the 61 catalog types (architecture plan, section 13.9).
 * The full catalog arrives as versioned data; here it only serves the interface.
 */
export const incidentTypesFixture: IncidentTypeView[] = [
  {
    key: 'co2_high',
    category: 'Atmosphere and life support',
    name: 'High CO₂',
    detection: 'AUTO',
    defaultSeverity: 'ALERT',
    evidenceState: 'VERIFIED',
    typicalZones: ['Any'],
    suggestedActions: ['Check ventilation and CO₂ filters', 'Measure CO₂ in local zones'],
  },
  {
    key: 'hypoxia',
    category: 'Atmosphere and life support',
    name: 'Hypoxia (low PIO₂)',
    detection: 'AUTO',
    defaultSeverity: 'CRITICAL',
    evidenceState: 'VERIFIED',
    typicalZones: ['Life support', 'Any'],
    suggestedActions: ['Check O₂ supply and pressure', 'Reduce physical exertion'],
  },
  {
    key: 'smoke_fire',
    category: 'Fire and smoke',
    name: 'Smoke or fire',
    detection: 'AUTO',
    defaultSeverity: 'CRITICAL',
    evidenceState: 'DEMO',
    typicalZones: ['Galley and mess', 'Engineering and propulsion', 'Storage'],
    suggestedActions: ['Activate the fire procedure', 'Isolate the zone'],
  },
  {
    key: 'burning_smell',
    category: 'Fire and smoke',
    name: 'Burning smell or overheating',
    detection: 'MANUAL',
    defaultSeverity: 'ALERT',
    evidenceState: 'DEMO',
    typicalZones: ['Any'],
    suggestedActions: ['Disconnect the suspect equipment', 'Inspect the zone'],
  },
  {
    key: 'injury',
    category: 'Crew health',
    name: 'Injury or accident',
    detection: 'MANUAL',
    defaultSeverity: 'ALERT',
    evidenceState: 'DEMO',
    typicalZones: ['Any'],
    suggestedActions: ['Attend and notify the Crew Medical Officer (CMO)'],
  },
  {
    key: 'loose_cargo',
    category: 'Cargo, equipment and science',
    name: 'Loose cargo or lost tool',
    detection: 'MANUAL',
    defaultSeverity: 'ATTENTION',
    evidenceState: 'DEMO',
    typicalZones: ['Storage'],
    suggestedActions: ['Secure the cargo and log the inventory'],
  },
]
