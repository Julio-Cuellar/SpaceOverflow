import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { App } from './App'

const openTab = (name: 'Cabin' | 'Ship' | 'Assistant') => userEvent.click(screen.getByRole('tab', { name }))

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
})
