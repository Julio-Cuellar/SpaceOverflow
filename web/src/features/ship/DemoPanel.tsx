import { useId, useState } from 'react'

/** Perfiles donde el modo demo se ve: desarrollo y jurado (plan, sección 7.7). */
const DEMO_PROFILES = ['dev1', 'dev2', 'jurado']

const SCENARIOS = [
  { key: 'fuga-presion', name: 'Fuga de presión' },
  { key: 'co2-alto', name: 'CO₂ alto' },
  { key: 'humedad', name: 'Humedad' },
  { key: 'fallo-o2', name: 'Fallo de O₂' },
  { key: 'calor', name: 'Calor' },
] as const

interface DemoPanelProps {
  profile: string
  zones: { id: string; name: string }[]
  onStart: (scenario: string, zoneId: string) => void
  onNormalize: () => void
}

/** Botones para provocar escenarios por zona y normalizar la nave. Solo en perfiles de demo. */
export function DemoPanel({ profile, zones, onStart, onNormalize }: DemoPanelProps) {
  const zoneId = useId()
  const [zone, setZone] = useState('')

  if (!DEMO_PROFILES.includes(profile)) return null

  return (
    <section aria-label="Modo demo">
      <label htmlFor={zoneId}>Zona del escenario</label>
      <select id={zoneId} value={zone} onChange={(e) => setZone(e.target.value)}>
        <option value="">Elegir zona</option>
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
            Provocar: {s.name}
          </button>
        ))}
      </div>

      <button type="button" onClick={onNormalize}>
        Normalizar todo
      </button>
    </section>
  )
}
