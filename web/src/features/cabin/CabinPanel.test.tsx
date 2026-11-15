import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { dashboardFixture } from '../../data/mocks/fixtures'
import { CabinPanel } from './CabinPanel'

describe('CabinPanel', () => {
  it('shows the worst severity of the habitat as the global status', () => {
    render(<CabinPanel dashboard={dashboardFixture('co2-alto')} />)

    expect(screen.getByRole('status', { name: 'Estado global' })).toHaveTextContent('Alerta')
  })

  it('shows each vital with its label, value and unit', () => {
    render(<CabinPanel dashboard={dashboardFixture('co2-alto')} />)

    expect(screen.getByText('CO₂ promedio de 1 h')).toBeInTheDocument()
    expect(screen.getByText('3.4 mmHg')).toBeInTheDocument()
  })

  it('marks body values with DEMO and with the simulated mark', () => {
    render(<CabinPanel dashboard={dashboardFixture('normal')} />)

    // Dos valores del cuerpo en el ejemplo: frecuencia cardíaca y SpO₂.
    expect(screen.getAllByText('SIMULADO')).toHaveLength(2)
    expect(screen.getAllByText('DEMO').length).toBeGreaterThanOrEqual(2)
  })

  it('never recalculates PIO2: it shows the value the backend sent', () => {
    render(<CabinPanel dashboard={dashboardFixture('normal')} />)

    expect(screen.getByText('149.7 mmHg')).toBeInTheDocument()
  })

  it('shows the waiting state instead of an empty panel when there are no readings yet', () => {
    render(<CabinPanel dashboard={{ ...dashboardFixture('normal'), vitals: [] }} />)

    expect(screen.getByText('Esperando lecturas del simulador')).toBeInTheDocument()
  })
})
