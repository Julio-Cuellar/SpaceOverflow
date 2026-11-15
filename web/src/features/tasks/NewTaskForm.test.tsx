import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { NewTaskForm } from './NewTaskForm'

const zones = [{ id: 'z-lab', name: 'Laboratorio' }]

function renderForm() {
  const onCreate = vi.fn()
  render(<NewTaskForm zones={zones} onCreate={onCreate} />)
  return onCreate
}

describe('NewTaskForm', () => {
  it('only offers health and ship tasks: incidents are opened by the system', () => {
    renderForm()

    const options = within(screen.getByLabelText('Tipo'))
      .getAllByRole('option')
      .map((o) => o.textContent)
    expect(options).toEqual(['Salud', 'Nave'])
  })

  it('does not allow sending without a title', () => {
    renderForm()

    expect(screen.getByRole('button', { name: 'Crear tarea' })).toBeDisabled()
  })

  it('creates a task with the chosen kind, zone and title', async () => {
    const onCreate = renderForm()

    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'Nave')
    await userEvent.selectOptions(screen.getByLabelText('Zona'), 'Laboratorio')
    await userEvent.type(screen.getByLabelText('Título'), 'Revisar el filtro')
    await userEvent.click(screen.getByRole('button', { name: 'Crear tarea' }))

    expect(onCreate).toHaveBeenCalledWith({ kind: 'NAVE', title: 'Revisar el filtro', zoneId: 'z-lab' })
  })

  it('leaves the zone empty when none is chosen and clears the title after creating', async () => {
    const onCreate = renderForm()

    await userEvent.type(screen.getByLabelText('Título'), 'Beber agua')
    await userEvent.click(screen.getByRole('button', { name: 'Crear tarea' }))

    expect(onCreate).toHaveBeenCalledWith({ kind: 'SALUD', title: 'Beber agua', zoneId: null })
    expect(screen.getByLabelText('Título')).toHaveValue('')
  })
})
