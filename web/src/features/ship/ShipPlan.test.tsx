import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Ticket, Zone } from './model'
import { ShipPlan } from './ShipPlan'

const zones: Zone[] = [
  {
    id: 'z-lab',
    name: 'Laboratory',
    layout: { x: 0, y: 0, w: 100, h: 60 },
    status: 'NORMAL',
  },
  {
    id: 'z-airlock',
    name: 'Airlock',
    layout: { x: 110, y: 0, w: 80, h: 60 },
    status: 'ALERT',
  },
]

const ticket = (id: string, code: string, zoneId: string): Ticket => ({
  id,
  code,
  title: 'High CO₂',
  severity: 'ALERT',
  status: 'OPEN',
  zoneId,
  source: 'ALERT',
  openedAt: '2026-11-14T10:00:00Z',
  valuesInRange: false,
})

describe('ShipPlan', () => {
  it('draws one area per zone from its layout data', () => {
    render(<ShipPlan zones={zones} tickets={[]} onSelectZone={() => {}} />)

    expect(screen.getByRole('button', { name: /Laboratory/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Airlock/ })).toBeInTheDocument()
  })

  it('names each zone with its status as text, not only with its color', () => {
    render(<ShipPlan zones={zones} tickets={[]} onSelectZone={() => {}} />)

    expect(screen.getByRole('button', { name: /Airlock, Alert/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Laboratory, Normal/ })).toBeInTheDocument()
  })

  it('pins the ticket identifier on its zone, with +n when there are more tickets', () => {
    render(
      <ShipPlan
        zones={zones}
        tickets={[ticket('t1', 'INC-0001', 'z-lab'), ticket('t2', 'INC-0002', 'z-lab')]}
        onSelectZone={() => {}}
      />,
    )

    expect(screen.getByText('INC-0001 +1')).toBeInTheDocument()
  })

  it('changes the drawn plan when the layout data changes, without code changes', () => {
    const { rerender } = render(<ShipPlan zones={zones} tickets={[]} onSelectZone={() => {}} />)

    rerender(
      <ShipPlan
        zones={[{ ...zones[0], name: 'Growing module' }]}
        tickets={[]}
        onSelectZone={() => {}}
      />,
    )

    expect(screen.getByRole('button', { name: /Growing module/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Laboratory/ })).not.toBeInTheDocument()
  })

  it('selects a zone by click and by keyboard, reporting its id', async () => {
    const onSelectZone = vi.fn()
    render(<ShipPlan zones={zones} tickets={[]} onSelectZone={onSelectZone} />)

    await userEvent.click(screen.getByRole('button', { name: /Airlock/ }))
    screen.getByRole('button', { name: /Laboratory/ }).focus()
    await userEvent.keyboard('{Enter}')

    expect(onSelectZone).toHaveBeenNthCalledWith(1, 'z-airlock')
    expect(onSelectZone).toHaveBeenNthCalledWith(2, 'z-lab')
  })

  it('also selects a zone with the space key', async () => {
    const onSelectZone = vi.fn()
    render(<ShipPlan zones={zones} tickets={[]} onSelectZone={onSelectZone} />)

    screen.getByRole('button', { name: /Airlock/ }).focus()
    await userEvent.keyboard(' ')

    expect(onSelectZone).toHaveBeenCalledWith('z-airlock')
  })

  it('pins a single ticket without a +n suffix', () => {
    render(
      <ShipPlan zones={zones} tickets={[ticket('t1', 'INC-0007', 'z-airlock')]} onSelectZone={() => {}} />,
    )

    expect(screen.getByText('INC-0007')).toBeInTheDocument()
  })

  it('does not pin resolved tickets on the plan', () => {
    render(
      <ShipPlan
        zones={zones}
        tickets={[{ ...ticket('t1', 'INC-0009', 'z-airlock'), status: 'RESOLVED' }]}
        onSelectZone={() => {}}
      />,
    )

    expect(screen.queryByText('INC-0009')).not.toBeInTheDocument()
  })

  it('draws a critical zone with a dashed outline, so the mark is not only color', () => {
    const critical: Zone[] = [{ ...zones[0], status: 'CRITICAL' }]
    const { container } = render(<ShipPlan zones={critical} tickets={[]} onSelectZone={() => {}} />)

    expect(container.querySelector('rect')).toHaveAttribute('stroke-dasharray', '6 4')
  })
})
