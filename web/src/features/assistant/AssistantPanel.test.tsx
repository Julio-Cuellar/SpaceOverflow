import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AssistantPanel } from './AssistantPanel'
import { mockAnswer, type AssistantAnswer } from './mockAnswer'

const answerFor = (question: string) => mockAnswer(question, [])

describe('AssistantPanel', () => {
  it('offers example questions the crew can tap instead of typing', async () => {
    render(<AssistantPanel answerFor={answerFor} mode="local" />)

    await userEvent.click(screen.getByRole('button', { name: 'Why do I have a headache?' }))

    expect(screen.getByText(/Headache between 2.8 and 4.5 mmHg/i)).toBeInTheDocument()
  })

  it('links each citation to its passage, with its evidence state next to it', async () => {
    render(<AssistantPanel answerFor={answerFor} mode="local" />)

    await userEvent.type(screen.getByLabelText('Question'), 'Why do I have a headache?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

    const link = screen.getByRole('link', { name: /OCHMO-TB-004 CO₂/ })
    expect(link.getAttribute('href')).toMatch(/^#pasaje\//)
    expect(within(link.closest('li') as HTMLElement).getByText('TB')).toBeInTheDocument()
  })

  it('says it has no information for a question without a passage', async () => {
    render(<AssistantPanel answerFor={answerFor} mode="local" />)

    await userEvent.type(screen.getByLabelText('Question'), 'How do I change the airlock filter?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

    expect(screen.getByText("I don't have that information in the loaded sources.")).toBeInTheDocument()
  })

  it('shows whether the answers come from the local or the cloud adapter', () => {
    const { rerender } = render(<AssistantPanel answerFor={answerFor} mode="local" />)
    expect(screen.getByText('Mode local')).toBeInTheDocument()

    rerender(<AssistantPanel answerFor={answerFor} mode="cloud" />)
    expect(screen.getByText('Mode cloud')).toBeInTheDocument()
  })

  it('does not allow sending an empty question, and clears the input after sending', async () => {
    render(<AssistantPanel answerFor={answerFor} mode="local" />)
    const send = screen.getByRole('button', { name: 'Ask' })
    expect(send).toBeDisabled()

    await userEvent.type(screen.getByLabelText('Question'), 'Why do I have a headache?')
    expect(send).toBeEnabled()
    await userEvent.click(send)

    expect(screen.getByLabelText('Question')).toHaveValue('')
  })

  describe('reading answers aloud', () => {
    const answerWith = (text: string): AssistantAnswer => ({ outcome: 'ANSWERED', text, citations: [] })

    it('offers no listen button when there is no voice service', async () => {
      render(<AssistantPanel answerFor={answerFor} mode="local" />)
      await userEvent.click(screen.getByRole('button', { name: 'Why do I have a headache?' }))

      expect(screen.queryByRole('button', { name: /Listen/ })).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Read answers aloud')).not.toBeInTheDocument()
    })

    it('reads an answer when the crew presses listen on it', async () => {
      const speak = vi.fn().mockResolvedValue(undefined)
      render(<AssistantPanel answerFor={() => answerWith('The limit is 3 mmHg.')} mode="local" speak={speak} />)
      await userEvent.type(screen.getByLabelText('Question'), 'limit')
      await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

      await userEvent.click(await screen.findByRole('button', { name: 'Listen to the answer' }))

      expect(speak).toHaveBeenCalledWith('The limit is 3 mmHg.')
    })

    it('does not read anything on its own while the option is off', async () => {
      const speak = vi.fn().mockResolvedValue(undefined)
      render(<AssistantPanel answerFor={() => answerWith('Answer.')} mode="local" speak={speak} />)

      await userEvent.type(screen.getByLabelText('Question'), 'question')
      await userEvent.click(screen.getByRole('button', { name: 'Ask' }))
      await screen.findByText('Answer.')

      expect(speak).not.toHaveBeenCalled()
    })

    it('reads each new answer by itself once the crew turns the option on', async () => {
      const speak = vi.fn().mockResolvedValue(undefined)
      render(<AssistantPanel answerFor={() => answerWith('Answer.')} mode="local" speak={speak} />)
      await userEvent.click(screen.getByLabelText('Read answers aloud'))

      await userEvent.type(screen.getByLabelText('Question'), 'question')
      await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

      await vi.waitFor(() => expect(speak).toHaveBeenCalledWith('Answer.'))
    })

    it('says the voice failed and keeps the answer on screen', async () => {
      const speak = vi.fn().mockRejectedValue(new Error('503'))
      render(<AssistantPanel answerFor={() => answerWith('Answer.')} mode="local" speak={speak} />)
      await userEvent.type(screen.getByLabelText('Question'), 'question')
      await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

      await userEvent.click(await screen.findByRole('button', { name: 'Listen to the answer' }))

      expect(await screen.findByRole('alert')).toHaveTextContent('Could not read it aloud')
      expect(screen.getByText('Answer.')).toBeVisible()
    })
  })

  describe('voice input', () => {
    const AUDIO = new Blob(['audio'])
    const voice = () => ({
      startRecording: vi.fn(async () => ({ stop: async () => AUDIO })),
      transcribe: vi.fn(async () => ({ text: 'Why do I have a headache?' })),
    })

    async function speak() {
      const user = userEvent.setup()
      const button = screen.getByRole('button', { name: 'Hold to talk' })
      await user.pointer([{ keys: '[MouseLeft>]', target: button }])
      await user.pointer([{ keys: '[/MouseLeft]', target: button }])
      return user
    }

    it('offers no voice button when no voice is connected: the text form always works', () => {
      render(<AssistantPanel answerFor={answerFor} mode="local" />)

      expect(screen.queryByRole('button', { name: 'Hold to talk' })).not.toBeInTheDocument()
      expect(screen.getByLabelText('Question')).toBeVisible()
    })

    it('does not ask anything until the crew confirms the transcript', async () => {
      render(<AssistantPanel answerFor={answerFor} mode="local" voice={voice()} />)

      await speak()

      expect(await screen.findByLabelText('Transcript (you can correct it)')).toBeVisible()
      expect(within(screen.getByRole('list', { name: 'Conversation' })).queryAllByRole('listitem')).toHaveLength(0)
    })

    it('asks the assistant with the confirmed text and shows the answer with its sources', async () => {
      render(<AssistantPanel answerFor={answerFor} mode="local" voice={voice()} />)

      const user = await speak()
      await user.click(await screen.findByRole('button', { name: 'Confirm and ask' }))

      const conversation = within(screen.getByRole('list', { name: 'Conversation' }))
      expect(conversation.getByText('Why do I have a headache?', { exact: false })).toBeVisible()
      expect(screen.getByText(/Headache between 2.8 and 4.5 mmHg/i)).toBeInTheDocument()
    })
  })
})

describe('AssistantPanel with a slow answer', () => {
  it('shows that it is consulting, blocks a second send, and then shows the answer', async () => {
    let resolve: (answer: AssistantAnswer) => void = () => {}
    const slow = () => new Promise<AssistantAnswer>((r) => (resolve = r))
    render(<AssistantPanel answerFor={slow} mode="local" />)

    await userEvent.type(screen.getByLabelText('Question'), 'Why do I have a headache?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

    expect(screen.getByRole('status')).toHaveTextContent('Consulting')
    expect(screen.getByText('You:', { exact: false })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled()

    await act(async () => resolve({ outcome: 'ANSWERED', text: 'Respuesta lista.', citations: [] }))

    expect(screen.getByText('Respuesta lista.')).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('tells the crew the consultation failed instead of showing an invented answer', async () => {
    const failing = () => Promise.reject(new Error('backend down'))
    render(<AssistantPanel answerFor={failing} mode="local" />)

    await userEvent.type(screen.getByLabelText('Question'), 'How long does space motion sickness last?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not consult the assistant')
    expect(screen.queryByText(/I don't have that information/)).not.toBeInTheDocument()
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

    await userEvent.type(screen.getByLabelText('Question'), 'question')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findAllByRole('link', { name: /NASA-STD-3001/ })).toHaveLength(3)
    expect(consoleError).not.toHaveBeenCalled()
    consoleError.mockRestore()
  })
})
