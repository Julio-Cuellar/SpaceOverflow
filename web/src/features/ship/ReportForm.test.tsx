import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { incidentTypesFixture } from '../../data/mocks/incidentTypes'
import { ReportForm } from './ReportForm'

const zones = [
  { id: 'z-cocina', name: 'Cocina y comedor' },
  { id: 'z-lab', name: 'Laboratorio' },
]

function renderForm(onReport = vi.fn()) {
  render(<ReportForm types={incidentTypesFixture} zones={zones} onReport={onReport} />)
  return onReport
}

describe('ReportForm', () => {
  it('offers only the types of the chosen category', async () => {
    renderForm()

    await userEvent.selectOptions(screen.getByLabelText('Categoría'), 'Fuego y humo')

    const options = within(screen.getByLabelText('Tipo'))
      .getAllByRole('option')
      .map((o) => o.textContent)
    expect(options).toEqual(['Elegir tipo', 'Humo o incendio', 'Olor a quemado o sobrecalentamiento'])
  })

  it('proposes the default severity of the chosen type', async () => {
    renderForm()

    await userEvent.selectOptions(screen.getByLabelText('Categoría'), 'Fuego y humo')
    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'Humo o incendio')

    expect(screen.getByLabelText('Severidad')).toHaveValue('CRITICO')
  })

  it('does not allow sending until a type and a zone are chosen', async () => {
    renderForm()

    expect(screen.getByRole('button', { name: 'Enviar reporte' })).toBeDisabled()

    await userEvent.selectOptions(screen.getByLabelText('Categoría'), 'Fuego y humo')
    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'Humo o incendio')
    await userEvent.selectOptions(screen.getByLabelText('Zona'), 'Cocina y comedor')

    expect(screen.getByRole('button', { name: 'Enviar reporte' })).toBeEnabled()
  })

  it('uses the type name as title when the crew leaves the title empty', async () => {
    const onReport = renderForm()

    await userEvent.selectOptions(screen.getByLabelText('Categoría'), 'Fuego y humo')
    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'Humo o incendio')
    await userEvent.selectOptions(screen.getByLabelText('Zona'), 'Cocina y comedor')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar reporte' }))

    expect(onReport).toHaveBeenCalledWith({
      typeKey: 'smoke_fire',
      zoneId: 'z-cocina',
      severity: 'CRITICO',
      title: 'Humo o incendio',
      description: '',
    })
  })

  it('sends the title and description the crew wrote', async () => {
    const onReport = renderForm()

    await userEvent.selectOptions(screen.getByLabelText('Categoría'), 'Fuego y humo')
    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'Olor a quemado o sobrecalentamiento')
    await userEvent.selectOptions(screen.getByLabelText('Zona'), 'Laboratorio')
    await userEvent.type(screen.getByLabelText('Título'), 'Olor en el panel')
    await userEvent.type(screen.getByLabelText('Descripción'), 'Huele a plástico caliente')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar reporte' }))

    expect(onReport).toHaveBeenCalledWith(
      expect.objectContaining({
        typeKey: 'burning_smell',
        title: 'Olor en el panel',
        description: 'Huele a plástico caliente',
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

    expect(screen.getByLabelText('Categoría')).toHaveValue('Atmósfera y soporte vital')
    expect(screen.getByLabelText('Tipo')).toHaveValue('hypoxia')
    expect(screen.getByLabelText('Severidad')).toHaveValue('CRITICO')
  })
})
