import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { incidentTypesFixture } from '../../data/mocks/incidentTypes'
import { CatalogList } from './CatalogList'

describe('CatalogList', () => {
  it('shows how many incident types the catalog has', () => {
    render(<CatalogList types={incidentTypesFixture} onReport={() => {}} />)

    expect(screen.getByText('6 types')).toBeInTheDocument()
  })

  it('filters the list by category', async () => {
    render(<CatalogList types={incidentTypesFixture} onReport={() => {}} />)

    await userEvent.selectOptions(screen.getByLabelText('Category'), 'Fire and smoke')

    const rows = screen.getAllByRole('listitem')
    expect(rows).toHaveLength(2)
    expect(within(rows[0]).getByText('Smoke or fire')).toBeInTheDocument()
  })

  it('shows whether each type is detected automatically or reported manually', () => {
    render(<CatalogList types={incidentTypesFixture} onReport={() => {}} />)

    const co2 = screen.getByText('High CO₂').closest('li') as HTMLElement
    const injury = screen.getByText('Injury or accident').closest('li') as HTMLElement
    expect(within(co2).getByText('AUTO')).toBeInTheDocument()
    expect(within(injury).getByText('MANUAL')).toBeInTheDocument()
  })

  it('pre-fills the report form when the crew presses Report', async () => {
    const onReport = vi.fn()
    render(<CatalogList types={incidentTypesFixture} onReport={onReport} />)

    const row = screen.getByText('Hypoxia (low PIO₂)').closest('li') as HTMLElement
    await userEvent.click(within(row).getByRole('button', { name: 'Report' }))

    expect(onReport).toHaveBeenCalledWith('hypoxia')
  })
})
