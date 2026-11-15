import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'

const openTab = (name: 'Cabin' | 'Ship' | 'Assistant' | 'Tasks') => userEvent.click(screen.getByRole('tab', { name }))

async function triggerCo2InLab() {
  await openTab('Ship')
  await userEvent.selectOptions(screen.getByLabelText('Scenario zone'), 'Laboratory')
  await userEvent.click(screen.getByRole('button', { name: 'Trigger: High CO₂' }))
}

describe('App', () => {
  it('opens on the cabin with the permanent banner and a normal global status', () => {
    render(<App />)

    expect(
      screen.getByText('Decision-support prototype. Not a medical device.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('status', { name: 'Global status' })).toHaveTextContent('Normal')
  })

  it('switches between the cabin and the ship panels', async () => {
    render(<App />)

    await openTab('Ship')
    expect(screen.getByRole('group', { name: 'Ship floor plan' })).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Cabin panel' })).not.toBeInTheDocument()

    await openTab('Cabin')
    expect(screen.getByRole('region', { name: 'Cabin panel' })).toBeInTheDocument()
  })

  it('shows the CO₂ alert with its actions first when the crew triggers it in the lab', async () => {
    render(<App />)
    await triggerCo2InLab()

    await openTab('Cabin')

    expect(screen.getByRole('status', { name: 'Global status' })).toHaveTextContent('Alert')
    expect(screen.getByRole('heading', { name: 'What to do' })).toBeInTheDocument()
    expect(screen.getByText('Probable cause: air')).toBeInTheDocument()
  })

  it('acknowledges the alert from the cabin panel', async () => {
    render(<App />)
    await triggerCo2InLab()
    await openTab('Cabin')

    await userEvent.click(screen.getByRole('button', { name: 'Acknowledge' }))

    expect(screen.getByText('Alert acknowledged')).toBeInTheDocument()
  })

  it('returns the cabin and the plan to normal with Normalize all', async () => {
    render(<App />)
    await triggerCo2InLab()
    await userEvent.click(screen.getByRole('button', { name: 'Normalize all' }))

    await openTab('Cabin')

    expect(screen.getByRole('status', { name: 'Global status' })).toHaveTextContent('Normal')
    expect(screen.queryByText('Probable cause: air')).not.toBeInTheDocument()
  })

  it('opens a ticket from the catalog, and the plan pins it on the chosen zone', async () => {
    render(<App />)
    await openTab('Ship')

    const row = screen.getByText('Hypoxia (low PIO₂)').closest('li') as HTMLElement
    await userEvent.click(within(row).getByRole('button', { name: 'Report' }))
    expect(screen.getByLabelText('Type')).toHaveValue('hypoxia')

    await userEvent.selectOptions(screen.getByLabelText('Zone'), 'Laboratory')
    await userEvent.click(screen.getByRole('button', { name: 'Submit report' }))

    expect(screen.getByRole('button', { name: /Laboratory/ })).toHaveTextContent('INC-0001')
  })

  it('shows the atmosphere charts of a zone when the crew selects it on the plan', async () => {
    render(<App />)
    await openTab('Ship')

    await userEvent.click(screen.getByRole('button', { name: /Laboratory/ }))

    expect(screen.getByRole('region', { name: 'Laboratory atmosphere' })).toBeInTheDocument()
  })

  it('answers a question from the assistant tab, citing its source', async () => {
    render(<App />)
    await openTab('Assistant')

    await userEvent.type(screen.getByLabelText('Question'), 'Why do I have a headache?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

    expect(screen.getByRole('link', { name: /OCHMO-TB-004 CO₂/ })).toBeInTheDocument()
  })

  it('mentions the active alert in its answer but never acknowledges or changes it', async () => {
    render(<App />)
    await triggerCo2InLab()
    await openTab('Assistant')

    await userEvent.type(screen.getByLabelText('Question'), 'Why do I have a headache?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))
    expect(screen.getByText(/Active alert: High CO₂ \((Alert)\)/)).toBeInTheDocument()

    await openTab('Cabin')
    expect(screen.getByRole('status', { name: 'Global status' })).toHaveTextContent('Alert')
    expect(screen.getByRole('button', { name: 'Acknowledge' })).toBeInTheDocument()
  })

  describe('tasks tab', () => {
    it('lists the daily tasks with the origin tag of each one', async () => {
      render(<App />)

      await openTab('Tasks')

      expect(screen.getByRole('region', { name: 'Daily tasks' })).toBeInTheDocument()
      expect(screen.getAllByText('Ground').length).toBeGreaterThan(0)
      expect(screen.getAllByText('System').length).toBeGreaterThan(0)
    })

    it('adds one to the streak when the crew completes a health routine', async () => {
      render(<App />)
      await openTab('Tasks')
      const before = Number(screen.getByText(/^Streak: \d+$/).textContent?.replace('Streak: ', ''))

      const routine = screen.getByRole('listitem', { name: 'Measure blood pressure' })
      await userEvent.click(within(routine).getByRole('button', { name: 'Complete' }))
      await userEvent.click(within(routine).getByRole('button', { name: 'Yes' }))

      expect(screen.getByText(`Streak: ${before + 1}`)).toBeVisible()
    })

    it('does not add to the streak when the crew completes a task from Earth', async () => {
      render(<App />)
      await openTab('Tasks')
      const before = screen.getByText(/^Streak: \d+$/).textContent

      const fromEarth = screen.getByRole('listitem', { name: '30-minute exercise' })
      await userEvent.click(within(fromEarth).getByRole('button', { name: 'Complete' }))
      await userEvent.click(within(fromEarth).getByRole('button', { name: 'Yes' }))

      expect(screen.getByText(/^Streak: \d+$/).textContent).toBe(before)
    })

    it('creates an own task that the crew can then delete, with no link to Earth needed', async () => {
      render(<App />)
      await openTab('Tasks')

      await userEvent.type(screen.getByLabelText('Title'), 'Check the filter del laboratorio')
      await userEvent.click(screen.getByRole('button', { name: 'Create task' }))
      const own = screen.getByRole('listitem', { name: 'Check the filter del laboratorio' })
      expect(within(own).getByText('Crew')).toBeVisible()

      await userEvent.click(within(own).getByRole('button', { name: 'Delete' }))
      expect(screen.queryByText('Check the filter del laboratorio')).not.toBeInTheDocument()
    })

    it('keeps a blocked task from Earth, with its reason', async () => {
      render(<App />)
      await openTab('Tasks')

      const fromEarth = screen.getByRole('listitem', { name: '30-minute exercise' })
      await userEvent.click(within(fromEarth).getByRole('button', { name: 'No puedo cumplirla' }))
      await userEvent.type(within(fromEarth).getByLabelText('Reason'), 'The treadmill is broken')
      await userEvent.click(within(fromEarth).getByRole('button', { name: 'Confirmar bloqueo' }))

      expect(screen.getByText(/The treadmill is broken/)).toBeVisible()
    })

    it('lets the crew stop sharing the state of its tasks', async () => {
      render(<App />)
      await openTab('Tasks')

      await userEvent.click(
        screen.getByRole('checkbox', { name: 'Share the status of my tasks with Ground' }),
      )

      expect(screen.getByText(/Ground will not see the status of your tasks/)).toBeVisible()
    })
  })

  it('offers voice in the assistant tab and, without a microphone, tells the crew to type', async () => {
    render(<App />)
    await openTab('Assistant')

    const button = screen.getByRole('button', { name: 'Hold to talk' })
    await userEvent.pointer([{ keys: '[MouseLeft>]', target: button }])
    await userEvent.pointer([{ keys: '[/MouseLeft]', target: button }])

    expect(await screen.findByRole('alert')).toHaveTextContent('type your question')
    expect(screen.getByLabelText('Question')).toBeVisible()
  })
})

describe('App with the real voice service', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('sends the recording to the voice service and shows its transcript, not the simulated one', async () => {
    class FakeRecorder {
      mimeType = 'audio/webm'
      ondataavailable: ((event: { data: Blob }) => void) | null = null
      onstop: (() => void) | null = null
      start() {}
      stop() {
        this.ondataavailable?.({ data: new Blob(['voice'], { type: 'audio/webm' }) })
        this.onstop?.()
      }
    }
    vi.stubGlobal('MediaRecorder', FakeRecorder)
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [] }) },
    })
    const transcribeVoice = vi.fn().mockResolvedValue({ text: 'what is the minimum cabin pressure' })
    render(<App transcribeVoice={transcribeVoice} />)
    await openTab('Assistant')

    const user = userEvent.setup()
    const button = screen.getByRole('button', { name: 'Hold to talk' })
    await user.pointer([{ keys: '[MouseLeft>]', target: button }])
    await user.pointer([{ keys: '[/MouseLeft]', target: button }])

    expect(await screen.findByDisplayValue('what is the minimum cabin pressure')).toBeVisible()
    expect(transcribeVoice).toHaveBeenCalledWith(expect.any(Blob))
    expect(screen.queryByText(/Simulated transcript/)).not.toBeInTheDocument()
  })
})

describe('App with the real voice output', () => {
  it('offers to read answers aloud only when a voice service is given', async () => {
    const { unmount } = render(<App />)
    await openTab('Assistant')
    expect(screen.queryByLabelText('Read answers aloud')).not.toBeInTheDocument()
    unmount()

    render(<App speak={vi.fn().mockResolvedValue(undefined)} />)
    await openTab('Assistant')
    expect(screen.getByLabelText('Read answers aloud')).toBeVisible()
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
    await openTab('Assistant')

    await userEvent.type(screen.getByLabelText('Question'), 'What is the noise limit in the crew quarters?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText('Respuesta de n8n.')).toBeInTheDocument()
    expect(askAssistant).toHaveBeenCalledWith('What is the noise limit in the crew quarters?')
  })
})
