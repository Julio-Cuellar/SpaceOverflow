import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { dashboardFixture } from '../../data/mocks/fixtures'
import { CabinPanel } from './CabinPanel'

describe('CabinPanel', () => {
  it('shows the worst severity of the habitat as the global status', () => {
    render(<CabinPanel dashboard={dashboardFixture('co2_slow')} />)

    expect(screen.getByRole('status', { name: 'Global status' })).toHaveTextContent('Alert')
  })

  it('shows each vital with its label, value and unit', () => {
    render(<CabinPanel dashboard={dashboardFixture('co2_slow')} />)

    expect(screen.getByText('1 h average CO₂')).toBeInTheDocument()
    expect(screen.getByText('3.4 mmHg')).toBeInTheDocument()
  })

  it('marks body values with DEMO and with the simulated mark', () => {
    render(<CabinPanel dashboard={dashboardFixture('normal')} />)

    // Two body values in the example: heart rate and SpO₂.
    expect(screen.getAllByText('SIMULATED')).toHaveLength(2)
    expect(screen.getAllByText('DEMO').length).toBeGreaterThanOrEqual(2)
  })

  it('never recalculates PIO2: it shows the value the backend sent', () => {
    render(<CabinPanel dashboard={dashboardFixture('normal')} />)

    expect(screen.getByText('149.7 mmHg')).toBeInTheDocument()
  })

  it('shows the waiting state instead of an empty panel when there are no readings yet', () => {
    render(<CabinPanel dashboard={{ ...dashboardFixture('normal'), vitals: [] }} />)

    expect(screen.getByText('Waiting for simulator readings')).toBeInTheDocument()
  })
})
