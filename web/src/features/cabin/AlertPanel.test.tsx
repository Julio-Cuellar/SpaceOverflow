import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AlertPanel, type AlertView } from './AlertPanel'

const co2Alert: AlertView = {
  severity: 'ALERT',
  ruleText: 'The 1-hour average ppCO₂ exceeds the standard limit of 3 mmHg.',
  measured: 'ppCO₂ 3.4 mmHg',
  causeHint: 'ENVIRONMENT',
  actions: [
    {
      key: 'check_ventilation_and_filters',
      title: 'Check ventilation and CO₂ filters',
      description: 'Check that the fans and filters are working.',
    },
    {
      key: 'measure_co2_in_local_zones',
      title: 'Measure CO₂ in local zones',
      description: 'Use a portable sensor in the zone where the value is rising.',
    },
  ],
  source: {
    documentCode: 'NASA-STD-3001 Vol. 2 Rev F',
    requirementRef: 'V2 6004',
    evidenceState: 'VERIFIED',
  },
  escalateWhen: 'If the value stays above 3 mmHg after checking ventilation.',
  body: 'This recommendation uses demo data, not NASA data.',
}

describe('AlertPanel', () => {
  it('shows what to do before why it happened', () => {
    render(<AlertPanel alert={co2Alert} onAcknowledge={() => {}} />)

    const actions = screen.getByRole('heading', { name: 'What to do' })
    const why = screen.getByRole('heading', { name: 'Why' })

    expect(actions.compareDocumentPosition(why) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('lists the actions in the order the catalog gives them', () => {
    render(<AlertPanel alert={co2Alert} onAcknowledge={() => {}} />)

    const items = screen.getAllByRole('listitem').map((li) => li.textContent)
    expect(items[0]).toContain('Check ventilation and CO₂ filters')
    expect(items[1]).toContain('Measure CO₂ in local zones')
  })

  it('names the probable cause as air or body, never as a diagnosis', () => {
    render(<AlertPanel alert={co2Alert} onAcknowledge={() => {}} />)

    expect(screen.getByText('Probable cause: air')).toBeInTheDocument()
  })

  it('shows the rule source with its document, requirement and evidence state', () => {
    render(<AlertPanel alert={co2Alert} onAcknowledge={() => {}} />)

    expect(screen.getByText(/NASA-STD-3001 Vol\. 2 Rev F · V2 6004/)).toBeInTheDocument()
    expect(screen.getByText('VERIFIED')).toBeInTheDocument()
  })

  it('shows only the document when the rule has no requirement', () => {
    render(
      <AlertPanel
        alert={{
          ...co2Alert,
          source: { documentCode: 'Demo (no requirement)', requirementRef: null, evidenceState: 'DEMO' },
        }}
        onAcknowledge={() => {}}
      />,
    )

    expect(screen.getByText(/Source: Demo \(no requirement\)/)).toBeInTheDocument()
    expect(screen.queryByText(/·/)).not.toBeInTheDocument()
  })

  it('says it is demo data when the recommendation comes from the demo source', () => {
    render(<AlertPanel alert={co2Alert} onAcknowledge={() => {}} />)

    expect(screen.getByText(/demo data, not NASA data/)).toBeInTheDocument()
  })

  it('announces a critical alert assertively to assistive technology', () => {
    const { container } = render(
      <AlertPanel alert={{ ...co2Alert, severity: 'CRITICAL' }} onAcknowledge={() => {}} />,
    )

    expect(container.querySelector('section')).toHaveAttribute('aria-live', 'assertive')
  })

  it('calls onAcknowledge when the crew presses Acknowledge', async () => {
    const onAcknowledge = vi.fn()
    render(<AlertPanel alert={co2Alert} onAcknowledge={onAcknowledge} />)

    await userEvent.click(screen.getByRole('button', { name: 'Acknowledge' }))

    expect(onAcknowledge).toHaveBeenCalledTimes(1)
  })
})
