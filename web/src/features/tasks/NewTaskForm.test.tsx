import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { NewTaskForm } from './NewTaskForm'

const zones = [{ id: 'z-lab', name: 'Laboratory' }]

function renderForm() {
  const onCreate = vi.fn()
  render(<NewTaskForm zones={zones} onCreate={onCreate} />)
  return onCreate
}

describe('NewTaskForm', () => {
  it('only offers health and ship tasks: incidents are opened by the system', () => {
    renderForm()

    const options = within(screen.getByLabelText('Type'))
      .getAllByRole('option')
      .map((o) => o.textContent)
    expect(options).toEqual(['Health', 'Ship'])
  })

  it('does not allow sending without a title', () => {
    renderForm()

    expect(screen.getByRole('button', { name: 'Create task' })).toBeDisabled()
  })

  it('creates a task with the chosen kind, zone and title', async () => {
    const onCreate = renderForm()

    await userEvent.selectOptions(screen.getByLabelText('Type'), 'Ship')
    await userEvent.selectOptions(screen.getByLabelText('Zone'), 'Laboratory')
    await userEvent.type(screen.getByLabelText('Title'), 'Check the filter')
    await userEvent.click(screen.getByRole('button', { name: 'Create task' }))

    expect(onCreate).toHaveBeenCalledWith({ kind: 'SHIP', title: 'Check the filter', zoneId: 'z-lab' })
  })

  it('leaves the zone empty when none is chosen and clears the title after creating', async () => {
    const onCreate = renderForm()

    await userEvent.type(screen.getByLabelText('Title'), 'Drink water')
    await userEvent.click(screen.getByRole('button', { name: 'Create task' }))

    expect(onCreate).toHaveBeenCalledWith({ kind: 'HEALTH', title: 'Drink water', zoneId: null })
    expect(screen.getByLabelText('Title')).toHaveValue('')
  })
})
