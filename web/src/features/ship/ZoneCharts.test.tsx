import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { Point } from '../charts/series'
import { ZoneCharts, type ZoneSeries } from './ZoneCharts'

const points: Point[] = [
  { t: 0, v: 1.0 },
  { t: 10, v: 1.2 },
]

const series: Record<string, ZoneSeries> = {
  o2: { label: 'O₂ (PIO₂)', unit: 'mmHg', points, evidenceState: 'VERIFICADO' },
  co2: { label: 'CO₂ (ppCO₂)', unit: 'mmHg', points, evidenceState: 'VERIFICADO' },
  n2: { label: 'N₂', unit: '%', points, evidenceState: 'VERIFICADO' },
  humedad: { label: 'Humedad', unit: '%', points, evidenceState: 'DEMO' },
  temperatura: { label: 'Temperatura', unit: '°C', points, evidenceState: 'DEMO' },
  presion: { label: 'Presión', unit: 'kPa', points, evidenceState: 'VERIFICADO' },
}

describe('ZoneCharts', () => {
  it('offers the six metrics of a zone as tabs', () => {
    render(<ZoneCharts zoneName="Laboratorio" series={series} />)

    expect(screen.getAllByRole('tab')).toHaveLength(6)
  })

  it('labels humidity and temperature as DEMO, and CO₂ as VERIFICADO', async () => {
    render(<ZoneCharts zoneName="Laboratorio" series={series} />)

    await userEvent.click(screen.getByRole('tab', { name: 'Humedad' }))
    expect(screen.getByText('DEMO')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: 'CO₂ (ppCO₂)' }))
    expect(screen.getByText('VERIFICADO')).toBeInTheDocument()
    expect(screen.queryByText('DEMO')).not.toBeInTheDocument()
  })

  it('shows the zone live and lets the crew pause and resume the updates', async () => {
    render(<ZoneCharts zoneName="Laboratorio" series={series} />)

    expect(screen.getByText('En vivo')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Pausar' }))
    expect(screen.getByText('En pausa')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Reanudar' }))
    expect(screen.getByText('En vivo')).toBeInTheDocument()
  })

  it('marks an anomaly reported by the backend with a text label', async () => {
    render(
      <ZoneCharts
        zoneName="Laboratorio"
        series={{ ...series, co2: { ...series.co2, anomaly: true } }}
      />,
    )

    await userEvent.click(screen.getByRole('tab', { name: 'CO₂ (ppCO₂)' }))

    expect(screen.getByText('ANOMALÍA')).toBeInTheDocument()
  })

  it('keeps the readings frozen while paused, and catches up on resume', async () => {
    const { rerender } = render(<ZoneCharts zoneName="Laboratorio" series={series} />)
    await userEvent.click(screen.getByRole('tab', { name: 'CO₂ (ppCO₂)' }))
    await userEvent.click(screen.getByRole('button', { name: 'Pausar' }))

    const newer = { ...series, co2: { ...series.co2, points: [...points, { t: 20, v: 3.4 }] } }
    rerender(<ZoneCharts zoneName="Laboratorio" series={newer} />)
    expect(screen.getByRole('img', { name: /último valor 1.2/ })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Reanudar' }))
    expect(screen.getByRole('img', { name: /último valor 3.4/ })).toBeInTheDocument()
  })
})
