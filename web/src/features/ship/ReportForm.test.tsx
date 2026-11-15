import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { incidentTypesFixture } from '../../data/mocks/incidentTypes'
import { ReportForm } from './ReportForm'

const zones = [
  { id: 'z-galley', name: 'Galley and mess' },
  { id: 'z-lab', name: 'Laboratory' },
]

function renderForm(onReport = vi.fn()) {
  render(<ReportForm types={incidentTypesFixture} zones={zones} onReport={onReport} />)
  return onReport
}

describe('ReportForm', () => {
  it('offers only the types of the chosen category', async () => {
    renderForm()

    await userEvent.selectOptions(screen.getByLabelText('Category'), 'Fire and smoke')

    const options = within(screen.getByLabelText('Type'))
      .getAllByRole('option')
      .map((o) => o.textContent)
    expect(options).toEqual(['Choose type', 'Smoke or fire', 'Burning smell or overheating'])
  })

  it('proposes the default severity of the chosen type', async () => {
    renderForm()

    await userEvent.selectOptions(screen.getByLabelText('Category'), 'Fire and smoke')
    await userEvent.selectOptions(screen.getByLabelText('Type'), 'Smoke or fire')

    expect(screen.getByLabelText('Severity')).toHaveValue('CRITICAL')
  })

  it('does not allow sending until a type and a zone are chosen', async () => {
    renderForm()

    expect(screen.getByRole('button', { name: 'Submit report' })).toBeDisabled()

    await userEvent.selectOptions(screen.getByLabelText('Category'), 'Fire and smoke')
    await userEvent.selectOptions(screen.getByLabelText('Type'), 'Smoke or fire')
    await userEvent.selectOptions(screen.getByLabelText('Zone'), 'Galley and mess')

    expect(screen.getByRole('button', { name: 'Submit report' })).toBeEnabled()
  })

  it('uses the type name as title when the crew leaves the title empty', async () => {
    const onReport = renderForm()

    await userEvent.selectOptions(screen.getByLabelText('Category'), 'Fire and smoke')
    await userEvent.selectOptions(screen.getByLabelText('Type'), 'Smoke or fire')
    await userEvent.selectOptions(screen.getByLabelText('Zone'), 'Galley and mess')
    await userEvent.click(screen.getByRole('button', { name: 'Submit report' }))

    expect(onReport).toHaveBeenCalledWith({
      typeKey: 'smoke_fire',
      zoneId: 'z-galley',
      severity: 'CRITICAL',
      title: 'Smoke or fire',
      description: '',
    })
  })

  it('sends the title and description the crew wrote', async () => {
    const onReport = renderForm()

    await userEvent.selectOptions(screen.getByLabelText('Category'), 'Fire and smoke')
    await userEvent.selectOptions(screen.getByLabelText('Type'), 'Burning smell or overheating')
    await userEvent.selectOptions(screen.getByLabelText('Zone'), 'Laboratory')
    await userEvent.type(screen.getByLabelText('Title'), 'Smell near the panel')
    await userEvent.type(screen.getByLabelText('Description'), 'Smells like hot plastic')
    await userEvent.click(screen.getByRole('button', { name: 'Submit report' }))

    expect(onReport).toHaveBeenCalledWith(
      expect.objectContaining({
        typeKey: 'burning_smell',
        title: 'Smell near the panel',
        description: 'Smells like hot plastic',
      }),
    )
  })

  it('starts with the type the catalog sent, with its category and severity', () => {
    render(
      <ReportForm
        types={incidentTypesFixture}
        zones={zones}
        onReport={() => {}}
        presetTypeKey="hypoxia"
      />,
    )

    expect(screen.getByLabelText('Category')).toHaveValue('Atmosphere and life support')
    expect(screen.getByLabelText('Type')).toHaveValue('hypoxia')
    expect(screen.getByLabelText('Severity')).toHaveValue('CRITICAL')
  })
})
