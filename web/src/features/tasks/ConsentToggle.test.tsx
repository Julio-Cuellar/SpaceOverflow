import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ConsentToggle } from './ConsentToggle'

describe('ConsentToggle', () => {
  it('shows the "tareas" category as shared by default and says what it shares', () => {
    render(<ConsentToggle shared onChange={vi.fn()} />)

    expect(screen.getByRole('checkbox', { name: 'Compartir el estado de mis tareas con Tierra' })).toBeChecked()
    expect(screen.getByRole('group', { name: 'Enlace y privacidad' })).toBeVisible()
  })

  it('reports the new value when the crew changes it', async () => {
    const onChange = vi.fn()
    render(<ConsentToggle shared onChange={onChange} />)

    await userEvent.click(screen.getByRole('checkbox'))

    expect(onChange).toHaveBeenCalledWith(false)
  })

  it('warns that nothing about tasks is sent while it is off', () => {
    render(<ConsentToggle shared={false} onChange={vi.fn()} />)

    expect(screen.getByText(/Tierra no verá el estado de tus tareas/)).toBeVisible()
  })
})
