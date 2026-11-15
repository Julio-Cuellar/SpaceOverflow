import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LineChart } from './LineChart'

const readings = [
  { t: 0, v: 1.0 },
  { t: 10, v: 3.4 },
]

describe('LineChart', () => {
  it('shows the empty state while there are no readings', () => {
    render(<LineChart label="1 h average CO₂" unit="mmHg" points={[]} />)

    expect(screen.getByText('Waiting for simulator readings')).toBeInTheDocument()
  })

  it('names the chart with its metric and its last value, for screen readers', () => {
    render(<LineChart label="1 h average CO₂" unit="mmHg" points={readings} />)

    expect(
      screen.getByRole('img', { name: '1 h average CO₂, last value 3.4 mmHg' }),
    ).toBeInTheDocument()
  })

  it('draws the threshold line and labels it with its value', () => {
    render(
      <LineChart
        label="1 h average CO₂"
        unit="mmHg"
        points={readings}
        threshold={{ value: 3, label: 'Threshold 3 mmHg' }}
      />,
    )

    expect(screen.getByText('Threshold 3 mmHg')).toBeInTheDocument()
  })

  it('marks an anomaly with a text label, not only with color', () => {
    render(<LineChart label="Humidity" unit="%" points={readings} anomaly />)

    expect(screen.getByText('ANOMALY')).toBeInTheDocument()
  })

  it('does not show the anomaly label when there is none', () => {
    render(<LineChart label="Humidity" unit="%" points={readings} />)

    expect(screen.queryByText('ANOMALY')).not.toBeInTheDocument()
  })
})
