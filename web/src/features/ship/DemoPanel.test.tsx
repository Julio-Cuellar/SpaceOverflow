import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { DemoPanel } from './DemoPanel'

const zones = [{ id: 'z-lab', name: 'Laboratorio' }]

describe('DemoPanel', () => {
  it('is visible in the development and jury profiles', () => {
    render(<DemoPanel profile="jurado" zones={zones} onStart={() => {}} onNormalize={() => {}} />)

    expect(screen.getByRole('region', { name: 'Modo demo' })).toBeInTheDocument()
  })

  it('is hidden in any other profile', () => {
    render(<DemoPanel profile="produccion" zones={zones} onStart={() => {}} onNormalize={() => {}} />)

    expect(screen.queryByRole('region', { name: 'Modo demo' })).not.toBeInTheDocument()
  })

  it('offers the five demo scenarios of the plan', () => {
    render(<DemoPanel profile="dev1" zones={zones} onStart={() => {}} onNormalize={() => {}} />)

    for (const name of ['Fuga de presión', 'CO₂ alto', 'Humedad', 'Fallo de O₂', 'Calor']) {
      expect(screen.getByRole('button', { name: `Provocar: ${name}` })).toBeInTheDocument()
    }
  })

  it('starts a scenario in the zone chosen by the presenter', async () => {
    const onStart = vi.fn()
    render(<DemoPanel profile="dev1" zones={zones} onStart={onStart} onNormalize={() => {}} />)

    await userEvent.selectOptions(screen.getByLabelText('Zona del escenario'), 'z-lab')
    await userEvent.click(screen.getByRole('button', { name: 'Provocar: CO₂ alto' }))

    expect(onStart).toHaveBeenCalledWith('co2-alto', 'z-lab')
  })

  it('normalizes every zone with one button', async () => {
    const onNormalize = vi.fn()
    render(<DemoPanel profile="dev1" zones={zones} onStart={() => {}} onNormalize={onNormalize} />)

    await userEvent.click(screen.getByRole('button', { name: 'Normalizar todo' }))

    expect(onNormalize).toHaveBeenCalledTimes(1)
  })
})
