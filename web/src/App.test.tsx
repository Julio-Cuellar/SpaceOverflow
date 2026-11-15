import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { App } from './App'

const openTab = (name: 'Cabina' | 'Nave' | 'Asistente' | 'Tareas') => userEvent.click(screen.getByRole('tab', { name }))

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

  describe('tasks tab', () => {
    it('lists the daily tasks with the origin tag of each one', async () => {
      render(<App />)

      await openTab('Tareas')

      expect(screen.getByRole('region', { name: 'Tareas del día' })).toBeInTheDocument()
      expect(screen.getAllByText('Tierra').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Sistema').length).toBeGreaterThan(0)
    })

    it('adds one to the streak when the crew completes a health routine', async () => {
      render(<App />)
      await openTab('Tareas')
      const before = Number(screen.getByText(/^Racha: \d+$/).textContent?.replace('Racha: ', ''))

      const routine = screen.getByRole('listitem', { name: 'Medir la presión arterial' })
      await userEvent.click(within(routine).getByRole('button', { name: 'Completar' }))
      await userEvent.click(within(routine).getByRole('button', { name: 'Sí' }))

      expect(screen.getByText(`Racha: ${before + 1}`)).toBeVisible()
    })

    it('does not add to the streak when the crew completes a task from Earth', async () => {
      render(<App />)
      await openTab('Tareas')
      const before = screen.getByText(/^Racha: \d+$/).textContent

      const fromEarth = screen.getByRole('listitem', { name: 'Ejercicio de 30 minutos' })
      await userEvent.click(within(fromEarth).getByRole('button', { name: 'Completar' }))
      await userEvent.click(within(fromEarth).getByRole('button', { name: 'Sí' }))

      expect(screen.getByText(/^Racha: \d+$/).textContent).toBe(before)
    })

    it('creates an own task that the crew can then delete, with no link to Earth needed', async () => {
      render(<App />)
      await openTab('Tareas')

      await userEvent.type(screen.getByLabelText('Título'), 'Revisar el filtro del laboratorio')
      await userEvent.click(screen.getByRole('button', { name: 'Crear tarea' }))
      const own = screen.getByRole('listitem', { name: 'Revisar el filtro del laboratorio' })
      expect(within(own).getByText('Tripulación')).toBeVisible()

      await userEvent.click(within(own).getByRole('button', { name: 'Eliminar' }))
      expect(screen.queryByText('Revisar el filtro del laboratorio')).not.toBeInTheDocument()
    })

    it('keeps a blocked task from Earth, with its reason', async () => {
      render(<App />)
      await openTab('Tareas')

      const fromEarth = screen.getByRole('listitem', { name: 'Ejercicio de 30 minutos' })
      await userEvent.click(within(fromEarth).getByRole('button', { name: 'No puedo cumplirla' }))
      await userEvent.type(within(fromEarth).getByLabelText('Motivo'), 'La cinta está averiada')
      await userEvent.click(within(fromEarth).getByRole('button', { name: 'Confirmar bloqueo' }))

      expect(screen.getByText(/La cinta está averiada/)).toBeVisible()
    })

    it('lets the crew stop sharing the state of its tasks', async () => {
      render(<App />)
      await openTab('Tareas')

      await userEvent.click(
        screen.getByRole('checkbox', { name: 'Compartir el estado de mis tareas con Tierra' }),
      )

      expect(screen.getByText(/Tierra no verá el estado de tus tareas/)).toBeVisible()
    })
  })

  it('offers voice in the assistant tab and, without a microphone, tells the crew to type', async () => {
    render(<App />)
    await openTab('Asistente')

    const button = screen.getByRole('button', { name: 'Mantener para hablar' })
    await userEvent.pointer([{ keys: '[MouseLeft>]', target: button }])
    await userEvent.pointer([{ keys: '[/MouseLeft]', target: button }])

    expect(await screen.findByRole('alert')).toHaveTextContent('escribe tu pregunta')
    expect(screen.getByLabelText('Pregunta')).toBeVisible()
  })
})

describe('App with the real assistant', () => {
  it('sends the question to the assistant it was given instead of the local simulation', async () => {
    const askAssistant = vi.fn().mockResolvedValue({
      outcome: 'ANSWERED',
      text: 'Respuesta de n8n.',
      citations: [],
    })
    render(<App askAssistant={askAssistant} />)
    await openTab('Asistente')

    await userEvent.type(screen.getByLabelText('Pregunta'), 'What is the noise limit in the crew quarters?')
    await userEvent.click(screen.getByRole('button', { name: 'Preguntar' }))

    expect(await screen.findByText('Respuesta de n8n.')).toBeInTheDocument()
    expect(askAssistant).toHaveBeenCalledWith('What is the noise limit in the crew quarters?')
  })
})
