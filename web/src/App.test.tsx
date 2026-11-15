import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { App } from './App'

const openTab = (name: 'Cabina' | 'Nave' | 'Asistente') => userEvent.click(screen.getByRole('tab', { name }))

async function provokeCo2InLab() {
  await openTab('Nave')
  await userEvent.selectOptions(screen.getByLabelText('Zona del escenario'), 'Laboratorio')
  await userEvent.click(screen.getByRole('button', { name: 'Provocar: CO₂ alto' }))
}

describe('App', () => {
  it('opens on the cabin with the permanent banner and a normal global status', () => {
    render(<App />)

    expect(
      screen.getByText('Prototipo de apoyo a la decisión. No es un dispositivo médico'),
    ).toBeInTheDocument()
    expect(screen.getByRole('status', { name: 'Estado global' })).toHaveTextContent('Normal')
  })

  it('switches between the cabin and the ship panels', async () => {
    render(<App />)

    await openTab('Nave')
    expect(screen.getByRole('group', { name: 'Plano de la nave' })).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Panel de cabina' })).not.toBeInTheDocument()

    await openTab('Cabina')
    expect(screen.getByRole('region', { name: 'Panel de cabina' })).toBeInTheDocument()
  })

  it('shows the CO₂ alert with its actions first when the crew provokes it in the lab', async () => {
    render(<App />)
    await provokeCo2InLab()

    await openTab('Cabina')

    expect(screen.getByRole('status', { name: 'Estado global' })).toHaveTextContent('Alerta')
    expect(screen.getByRole('heading', { name: 'Qué hacer' })).toBeInTheDocument()
    expect(screen.getByText('Causa probable: aire')).toBeInTheDocument()
  })

  it('acknowledges the alert from the cabin panel', async () => {
    render(<App />)
    await provokeCo2InLab()
    await openTab('Cabina')

    await userEvent.click(screen.getByRole('button', { name: 'Reconocer' }))

    expect(screen.getByText('Alerta reconocida')).toBeInTheDocument()
  })

  it('returns the cabin and the plan to normal with Normalizar todo', async () => {
    render(<App />)
    await provokeCo2InLab()
    await userEvent.click(screen.getByRole('button', { name: 'Normalizar todo' }))

    await openTab('Cabina')

    expect(screen.getByRole('status', { name: 'Estado global' })).toHaveTextContent('Normal')
    expect(screen.queryByText('Causa probable: aire')).not.toBeInTheDocument()
  })

  it('opens a ticket from the catalog, and the plan pins it on the chosen zone', async () => {
    render(<App />)
    await openTab('Nave')

    const row = screen.getByText('Hipoxia (PIO₂ baja)').closest('li') as HTMLElement
    await userEvent.click(within(row).getByRole('button', { name: 'Reportar' }))
    expect(screen.getByLabelText('Tipo')).toHaveValue('hypoxia')

    await userEvent.selectOptions(screen.getByLabelText('Zona'), 'Laboratorio')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar reporte' }))

    expect(screen.getByRole('button', { name: /Laboratorio/ })).toHaveTextContent('INC-0001')
  })

  it('shows the atmosphere charts of a zone when the crew selects it on the plan', async () => {
    render(<App />)
    await openTab('Nave')

    await userEvent.click(screen.getByRole('button', { name: /Laboratorio/ }))

    expect(screen.getByRole('region', { name: 'Atmósfera de Laboratorio' })).toBeInTheDocument()
  })

  it('answers a question from the assistant tab, citing its source', async () => {
    render(<App />)
    await openTab('Asistente')

    await userEvent.type(screen.getByLabelText('Pregunta'), '¿Por qué me duele la cabeza?')
    await userEvent.click(screen.getByRole('button', { name: 'Preguntar' }))

    expect(screen.getByRole('link', { name: /OCHMO-TB-004 CO₂/ })).toBeInTheDocument()
  })

  it('mentions the active alert in its answer but never acknowledges or changes it', async () => {
    render(<App />)
    await provokeCo2InLab()
    await openTab('Asistente')

    await userEvent.type(screen.getByLabelText('Pregunta'), '¿Por qué me duele la cabeza?')
    await userEvent.click(screen.getByRole('button', { name: 'Preguntar' }))
    expect(screen.getByText(/Alerta activa: CO₂ alto \(Alerta\)/)).toBeInTheDocument()

    await openTab('Cabina')
    expect(screen.getByRole('status', { name: 'Estado global' })).toHaveTextContent('Alerta')
    expect(screen.getByRole('button', { name: 'Reconocer' })).toBeInTheDocument()
  })
})
