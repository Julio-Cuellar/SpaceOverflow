import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { BodyMap, type BodyIndicator } from './BodyMap'

const indicators: BodyIndicator[] = [
  { key: 'cabeza', label: 'Cabeza', value: 'Cefalea leve', severity: 'ATENCION', hazard: 'entorno', evidenceState: 'DEMO' },
  { key: 'pulmones', label: 'Pulmones', value: 'SpO₂ 98 %', severity: 'NORMAL', hazard: 'entorno', evidenceState: 'DEMO' },
  { key: 'corazon', label: 'Corazón', value: '72 lpm', severity: 'NORMAL', hazard: 'gravedad', evidenceState: 'DEMO' },
  { key: 'sangre', label: 'Sangre y órganos', value: 'Radiación acumulada baja', severity: 'NORMAL', hazard: 'radiacion', evidenceState: 'DEMO' },
  { key: 'temperatura', label: 'Temperatura', value: '36.6 °C', severity: 'NORMAL', hazard: 'entorno', evidenceState: 'DEMO' },
  { key: 'huesos', label: 'Huesos y músculo', value: 'Línea base al 95 %', severity: 'NORMAL', hazard: 'gravedad', evidenceState: 'DEMO' },
]

describe('BodyMap', () => {
  it('renders the six indicators of the human body panel', () => {
    render(<BodyMap indicators={indicators} />)

    expect(screen.getAllByRole('button')).toHaveLength(6)
  })

  it('names each indicator with its status as text, not only with its color', () => {
    render(<BodyMap indicators={indicators} />)

    expect(screen.getByRole('button', { name: 'Corazón, Normal' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cabeza, Atención' })).toBeInTheDocument()
  })

  it('shows the value, the NASA hazard and the evidence of a tapped indicator', async () => {
    render(<BodyMap indicators={indicators} />)

    await userEvent.click(screen.getByRole('button', { name: 'Corazón, Normal' }))

    const detail = screen.getByRole('region', { name: 'Detalle' })
    expect(within(detail).getByText('72 lpm')).toBeInTheDocument()
    expect(within(detail).getByText('Peligro del programa de NASA: Campos gravitacionales')).toBeInTheDocument()
    expect(within(detail).getByText('DEMO')).toBeInTheDocument()
  })

  it('says the body values are simulated, for demonstration only', () => {
    render(<BodyMap indicators={indicators} />)

    expect(screen.getByText(/Valores simulados, de demostración/)).toBeInTheDocument()
  })

  it('shows no detail until an indicator is tapped', () => {
    render(<BodyMap indicators={indicators} />)

    expect(screen.queryByRole('region', { name: 'Detalle' })).not.toBeInTheDocument()
  })
})
