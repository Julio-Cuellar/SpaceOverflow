import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { AssistantPanel } from './AssistantPanel'
import { mockAnswer } from './mockAnswer'

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
    expect(link.getAttribute('href')).toMatch(/^#passage\//)
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
    expect(screen.getByText('Local mode')).toBeInTheDocument()

    rerender(<AssistantPanel answerFor={answerFor} mode="cloud" />)
    expect(screen.getByText('Cloud mode')).toBeInTheDocument()
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
})
