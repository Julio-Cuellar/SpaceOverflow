import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { AssistantPanel } from './AssistantPanel'
import { mockAnswer } from './mockAnswer'

const answerFor = (question: string) => mockAnswer(question, [])

describe('AssistantPanel', () => {
  it('offers example questions the crew can tap instead of typing', async () => {
    render(<AssistantPanel answerFor={answerFor} mode="local" />)

    await userEvent.click(screen.getByRole('button', { name: '¿Por qué me duele la cabeza?' }))

    expect(screen.getByText(/Dolor de cabeza entre 2.8 y 4.5 mmHg/i)).toBeInTheDocument()
  })

  it('links each citation to its passage, with its evidence state next to it', async () => {
    render(<AssistantPanel answerFor={answerFor} mode="local" />)

    await userEvent.type(screen.getByLabelText('Pregunta'), '¿Por qué me duele la cabeza?')
    await userEvent.click(screen.getByRole('button', { name: 'Preguntar' }))

    const link = screen.getByRole('link', { name: /OCHMO-TB-004 CO₂/ })
    expect(link.getAttribute('href')).toMatch(/^#pasaje\//)
    expect(within(link.closest('li') as HTMLElement).getByText('TB')).toBeInTheDocument()
  })

  it('says it has no information for a question without a passage', async () => {
    render(<AssistantPanel answerFor={answerFor} mode="local" />)

    await userEvent.type(screen.getByLabelText('Pregunta'), '¿Cómo cambio el filtro de la esclusa?')
    await userEvent.click(screen.getByRole('button', { name: 'Preguntar' }))

    expect(screen.getByText('No tengo esa información en las fuentes cargadas.')).toBeInTheDocument()
  })

  it('shows whether the answers come from the local or the cloud adapter', () => {
    const { rerender } = render(<AssistantPanel answerFor={answerFor} mode="local" />)
    expect(screen.getByText('Modo local')).toBeInTheDocument()

    rerender(<AssistantPanel answerFor={answerFor} mode="nube" />)
    expect(screen.getByText('Modo nube')).toBeInTheDocument()
  })

  it('does not allow sending an empty question, and clears the input after sending', async () => {
    render(<AssistantPanel answerFor={answerFor} mode="local" />)
    const send = screen.getByRole('button', { name: 'Preguntar' })
    expect(send).toBeDisabled()

    await userEvent.type(screen.getByLabelText('Pregunta'), '¿Por qué me duele la cabeza?')
    expect(send).toBeEnabled()
    await userEvent.click(send)

    expect(screen.getByLabelText('Pregunta')).toHaveValue('')
  })
})
