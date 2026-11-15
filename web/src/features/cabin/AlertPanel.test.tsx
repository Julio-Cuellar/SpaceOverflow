import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AlertPanel, type AlertView } from './AlertPanel'

const co2Alert: AlertView = {
  severity: 'ALERTA',
  ruleText: 'El promedio de 1 hora de ppCO₂ supera el límite de 3 mmHg de la norma.',
  measured: 'ppCO₂ 3.4 mmHg',
  causeHint: 'AMBIENTE',
  actions: [
    {
      key: 'revisar_ventilacion_y_filtros',
      title: 'Revisar ventilación y filtros de CO₂',
      description: 'Comprobar que los ventiladores y los filtros funcionan.',
    },
    {
      key: 'medir_co2_en_zonas_locales',
      title: 'Medir CO₂ en zonas locales',
      description: 'Usar un sensor portátil en la zona donde sube el valor.',
    },
  ],
  source: {
    documentCode: 'NASA-STD-3001 Vol. 2 Rev F',
    requirementRef: 'V2 6004',
    evidenceState: 'VERIFICADO',
  },
  escalateWhen: 'Si el valor sigue por encima de 3 mmHg tras revisar la ventilación.',
  body: 'Esta recomendación usa un dato de demostración, no de NASA.',
}

describe('AlertPanel', () => {
  it('shows what to do before why it happened', () => {
    render(<AlertPanel alert={co2Alert} onAcknowledge={() => {}} />)

    const actions = screen.getByRole('heading', { name: 'Qué hacer' })
    const why = screen.getByRole('heading', { name: 'Por qué' })

    expect(actions.compareDocumentPosition(why) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('lists the actions in the order the catalog gives them', () => {
    render(<AlertPanel alert={co2Alert} onAcknowledge={() => {}} />)

    const items = screen.getAllByRole('listitem').map((li) => li.textContent)
    expect(items[0]).toContain('Revisar ventilación y filtros de CO₂')
    expect(items[1]).toContain('Medir CO₂ en zonas locales')
  })

  it('names the probable cause as air or body, never as a diagnosis', () => {
    render(<AlertPanel alert={co2Alert} onAcknowledge={() => {}} />)

    expect(screen.getByText('Causa probable: aire')).toBeInTheDocument()
  })

  it('shows the rule source with its document, requirement and evidence state', () => {
    render(<AlertPanel alert={co2Alert} onAcknowledge={() => {}} />)

    expect(screen.getByText(/NASA-STD-3001 Vol\. 2 Rev F · V2 6004/)).toBeInTheDocument()
    expect(screen.getByText('VERIFICADO')).toBeInTheDocument()
  })

  it('shows only the document when the rule has no requirement', () => {
    render(
      <AlertPanel
        alert={{
          ...co2Alert,
          source: { documentCode: 'Demostración (sin requisito)', requirementRef: null, evidenceState: 'DEMO' },
        }}
        onAcknowledge={() => {}}
      />,
    )

    expect(screen.getByText(/Fuente: Demostración \(sin requisito\)/)).toBeInTheDocument()
    expect(screen.queryByText(/·/)).not.toBeInTheDocument()
  })

  it('says it is demo data when the recommendation comes from the demo source', () => {
    render(<AlertPanel alert={co2Alert} onAcknowledge={() => {}} />)

    expect(screen.getByText(/dato de demostración, no de NASA/)).toBeInTheDocument()
  })

  it('announces a critical alert assertively to assistive technology', () => {
    const { container } = render(
      <AlertPanel alert={{ ...co2Alert, severity: 'CRITICO' }} onAcknowledge={() => {}} />,
    )

    expect(container.querySelector('section')).toHaveAttribute('aria-live', 'assertive')
  })

  it('calls onAcknowledge when the crew presses Reconocer', async () => {
    const onAcknowledge = vi.fn()
    render(<AlertPanel alert={co2Alert} onAcknowledge={onAcknowledge} />)

    await userEvent.click(screen.getByRole('button', { name: 'Reconocer' }))

    expect(onAcknowledge).toHaveBeenCalledTimes(1)
  })
})
