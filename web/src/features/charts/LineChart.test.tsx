import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LineChart } from './LineChart'

const readings = [
  { t: 0, v: 1.0 },
  { t: 10, v: 3.4 },
]

describe('LineChart', () => {
  it('shows the empty state while there are no readings', () => {
    render(<LineChart label="CO₂ promedio de 1 h" unit="mmHg" points={[]} />)

    expect(screen.getByText('Esperando lecturas del simulador')).toBeInTheDocument()
  })

  it('names the chart with its metric and its last value, for screen readers', () => {
    render(<LineChart label="CO₂ promedio de 1 h" unit="mmHg" points={readings} />)

    expect(
      screen.getByRole('img', { name: 'CO₂ promedio de 1 h, último valor 3.4 mmHg' }),
    ).toBeInTheDocument()
  })

  it('draws the threshold line and labels it with its value', () => {
    render(
      <LineChart
        label="CO₂ promedio de 1 h"
        unit="mmHg"
        points={readings}
        threshold={{ value: 3, label: 'Umbral 3 mmHg' }}
      />,
    )

    expect(screen.getByText('Umbral 3 mmHg')).toBeInTheDocument()
  })

  it('marks an anomaly with a text label, not only with color', () => {
    render(<LineChart label="Humedad" unit="%" points={readings} anomaly />)

    expect(screen.getByText('ANOMALÍA')).toBeInTheDocument()
  })

  it('does not show the anomaly label when there is none', () => {
    render(<LineChart label="Humedad" unit="%" points={readings} />)

    expect(screen.queryByText('ANOMALÍA')).not.toBeInTheDocument()
  })
})
