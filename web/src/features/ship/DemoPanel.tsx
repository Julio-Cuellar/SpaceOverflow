import { useId, useState } from 'react'

/** Profiles where demo mode is visible: development and jury (architecture plan, section 7.7). */
const DEMO_PROFILES = ['dev1', 'dev2', 'jury']

const SCENARIOS = [
  { key: 'pressure_leak', name: 'Pressure leak' },
  { key: 'co2_slow', name: 'High CO₂' },
  { key: 'humidity_high', name: 'Humidity' },
  { key: 'o2_failure', name: 'O₂ failure' },
  { key: 'heat', name: 'Heat' },
] as const

interface DemoPanelProps {
  profile: string
  zones: { id: string; name: string }[]
  onStart: (scenario: string, zoneId: string) => void
  onNormalize: () => void
}

/** Buttons to trigger scenarios per zone and normalize the ship. Only in demo profiles. */
export function DemoPanel({ profile, zones, onStart, onNormalize }: DemoPanelProps) {
  const zoneId = useId()
  const [zone, setZone] = useState('')

  if (!DEMO_PROFILES.includes(profile)) return null

  return (
    <section aria-label="Demo mode">
      <label htmlFor={zoneId}>Scenario zone</label>
      <select id={zoneId} value={zone} onChange={(e) => setZone(e.target.value)}>
        <option value="">Choose zone</option>
        {zones.map((z) => (
          <option key={z.id} value={z.id}>
            {z.name}
          </option>
        ))}
      </select>

      <div>
        {SCENARIOS.map((s) => (
          <button
            key={s.key}
            type="button"
            disabled={zone === ''}
            onClick={() => onStart(s.key, zone)}
          >
            Trigger: {s.name}
          </button>
        ))}
      </div>

      <button type="button" onClick={onNormalize}>
        Normalize all
      </button>
    </section>
  )
}
