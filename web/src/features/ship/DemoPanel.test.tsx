import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { DemoPanel } from './DemoPanel'

const zones = [{ id: 'z-lab', name: 'Laboratory' }]

describe('DemoPanel', () => {
  it('is visible in the development and jury profiles', () => {
    render(<DemoPanel profile="jury" zones={zones} onStart={() => {}} onNormalize={() => {}} />)

    expect(screen.getByRole('region', { name: 'Demo mode' })).toBeInTheDocument()
  })

  it('is hidden in any other profile', () => {
    render(<DemoPanel profile="production" zones={zones} onStart={() => {}} onNormalize={() => {}} />)

    expect(screen.queryByRole('region', { name: 'Demo mode' })).not.toBeInTheDocument()
  })

  it('offers the five demo scenarios of the plan', () => {
    render(<DemoPanel profile="dev1" zones={zones} onStart={() => {}} onNormalize={() => {}} />)

    for (const name of ['Pressure leak', 'High CO₂', 'Humidity', 'O₂ failure', 'Heat']) {
      expect(screen.getByRole('button', { name: `Trigger: ${name}` })).toBeInTheDocument()
    }
  })

  it('starts a scenario in the zone chosen by the presenter', async () => {
    const onStart = vi.fn()
    render(<DemoPanel profile="dev1" zones={zones} onStart={onStart} onNormalize={() => {}} />)

    await userEvent.selectOptions(screen.getByLabelText('Scenario zone'), 'z-lab')
    await userEvent.click(screen.getByRole('button', { name: 'Trigger: High CO₂' }))

    expect(onStart).toHaveBeenCalledWith('co2_slow', 'z-lab')
  })

  it('normalizes every zone with one button', async () => {
    const onNormalize = vi.fn()
    render(<DemoPanel profile="dev1" zones={zones} onStart={() => {}} onNormalize={onNormalize} />)

    await userEvent.click(screen.getByRole('button', { name: 'Normalize all' }))

    expect(onNormalize).toHaveBeenCalledTimes(1)
  })
})
