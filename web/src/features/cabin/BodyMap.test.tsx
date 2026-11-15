import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { BodyMap, type BodyIndicator } from './BodyMap'

const indicators: BodyIndicator[] = [
  { key: 'head', label: 'Head', value: 'Mild headache', severity: 'ATTENTION', hazard: 'environment', evidenceState: 'DEMO' },
  { key: 'lungs', label: 'Lungs', value: 'SpO₂ 98 %', severity: 'NORMAL', hazard: 'environment', evidenceState: 'DEMO' },
  { key: 'heart', label: 'Heart', value: '72 bpm', severity: 'NORMAL', hazard: 'gravity', evidenceState: 'DEMO' },
  { key: 'blood', label: 'Blood and organs', value: 'Low accumulated radiation', severity: 'NORMAL', hazard: 'radiation', evidenceState: 'DEMO' },
  { key: 'temperature', label: 'Temperature', value: '36.6 °C', severity: 'NORMAL', hazard: 'environment', evidenceState: 'DEMO' },
  { key: 'bones', label: 'Bones and muscle', value: 'Baseline at 95 %', severity: 'NORMAL', hazard: 'gravity', evidenceState: 'DEMO' },
]

describe('BodyMap', () => {
  it('renders the six indicators of the human body panel', () => {
    render(<BodyMap indicators={indicators} />)

    expect(screen.getAllByRole('button')).toHaveLength(6)
  })

  it('names each indicator with its status as text, not only with its color', () => {
    render(<BodyMap indicators={indicators} />)

    expect(screen.getByRole('button', { name: 'Heart, Normal' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Head, Attention' })).toBeInTheDocument()
  })

  it('shows the value, the NASA hazard and the evidence of a tapped indicator', async () => {
    render(<BodyMap indicators={indicators} />)

    await userEvent.click(screen.getByRole('button', { name: 'Heart, Normal' }))

    const detail = screen.getByRole('region', { name: 'Detail' })
    expect(within(detail).getByText('72 bpm')).toBeInTheDocument()
    expect(within(detail).getByText('NASA program hazard: Gravity fields')).toBeInTheDocument()
    expect(within(detail).getByText('DEMO')).toBeInTheDocument()
  })

  it('says the body values are simulated, for demonstration only', () => {
    render(<BodyMap indicators={indicators} />)

    expect(screen.getByText(/Simulated values, for demonstration/)).toBeInTheDocument()
  })

  it('shows no detail until an indicator is tapped', () => {
    render(<BodyMap indicators={indicators} />)

    expect(screen.queryByRole('region', { name: 'Detail' })).not.toBeInTheDocument()
  })
})
