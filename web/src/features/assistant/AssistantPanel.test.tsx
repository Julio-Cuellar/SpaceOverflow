import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AssistantPanel } from './AssistantPanel'
import { mockAnswer, type AssistantAnswer } from './mockAnswer'

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

  describe('voice input', () => {
    const AUDIO = new Blob(['audio'])
    const voice = () => ({
      startRecording: vi.fn(async () => ({ stop: async () => AUDIO })),
      transcribe: vi.fn(async () => ({ text: '¿Por qué me duele la cabeza?' })),
    })

    async function speak() {
      const user = userEvent.setup()
      const button = screen.getByRole('button', { name: 'Mantener para hablar' })
      await user.pointer([{ keys: '[MouseLeft>]', target: button }])
      await user.pointer([{ keys: '[/MouseLeft]', target: button }])
      return user
    }

    it('offers no voice button when no voice is connected: the text form always works', () => {
      render(<AssistantPanel answerFor={answerFor} mode="local" />)

      expect(screen.queryByRole('button', { name: 'Mantener para hablar' })).not.toBeInTheDocument()
      expect(screen.getByLabelText('Pregunta')).toBeVisible()
    })

    it('does not ask anything until the crew confirms the transcript', async () => {
      render(<AssistantPanel answerFor={answerFor} mode="local" voice={voice()} />)

      await speak()

      expect(await screen.findByLabelText('Transcripción (puedes corregirla)')).toBeVisible()
      expect(within(screen.getByRole('list', { name: 'Conversación' })).queryAllByRole('listitem')).toHaveLength(0)
    })

    it('asks the assistant with the confirmed text and shows the answer with its sources', async () => {
      render(<AssistantPanel answerFor={answerFor} mode="local" voice={voice()} />)

      const user = await speak()
      await user.click(await screen.findByRole('button', { name: 'Confirmar y preguntar' }))

      const conversation = within(screen.getByRole('list', { name: 'Conversación' }))
      expect(conversation.getByText('¿Por qué me duele la cabeza?', { exact: false })).toBeVisible()
      expect(screen.getByText(/Dolor de cabeza entre 2.8 y 4.5 mmHg/i)).toBeInTheDocument()
    })
  })
})

describe('AssistantPanel with a slow answer', () => {
  it('shows that it is consulting, blocks a second send, and then shows the answer', async () => {
    let resolve: (answer: AssistantAnswer) => void = () => {}
    const slow = () => new Promise<AssistantAnswer>((r) => (resolve = r))
    render(<AssistantPanel answerFor={slow} mode="local" />)

    await userEvent.type(screen.getByLabelText('Pregunta'), '¿Por qué me duele la cabeza?')
    await userEvent.click(screen.getByRole('button', { name: 'Preguntar' }))

    expect(screen.getByRole('status')).toHaveTextContent('Consultando')
    expect(screen.getByText('Tú:', { exact: false })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Preguntar' })).toBeDisabled()

    await act(async () => resolve({ outcome: 'ANSWERED', text: 'Respuesta lista.', citations: [] }))

    expect(screen.getByText('Respuesta lista.')).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('tells the crew the consultation failed instead of showing an invented answer', async () => {
    const failing = () => Promise.reject(new Error('backend caído'))
    render(<AssistantPanel answerFor={failing} mode="local" />)

    await userEvent.type(screen.getByLabelText('Pregunta'), '¿Cuánto dura el mareo espacial?')
    await userEvent.click(screen.getByRole('button', { name: 'Preguntar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo consultar el asistente')
    expect(screen.queryByText(/No tengo esa información/)).not.toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})

describe('AssistantPanel with several citations from one document', () => {
  it('lists every citation without repeating React keys', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const citation = {
      documentCode: 'NASA-STD-3001 Vol. 2 Rev F',
      requirementRef: null,
      excerpt: 'texto',
      evidenceState: 'VERIFICADO' as const,
    }
    const answer = { outcome: 'ANSWERED' as const, text: 'Respuesta.', citations: [citation, citation, citation] }
    render(<AssistantPanel answerFor={() => Promise.resolve(answer)} mode="local" />)

    await userEvent.type(screen.getByLabelText('Pregunta'), 'pregunta')
    await userEvent.click(screen.getByRole('button', { name: 'Preguntar' }))

    expect(await screen.findAllByRole('link', { name: /NASA-STD-3001/ })).toHaveLength(3)
    expect(consoleError).not.toHaveBeenCalled()
    consoleError.mockRestore()
  })
})
