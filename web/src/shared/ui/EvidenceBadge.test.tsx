import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EvidenceBadge } from './EvidenceBadge'

describe('EvidenceBadge', () => {
  it('labels each evidence state with its own text', () => {
    const { rerender } = render(<EvidenceBadge state="VERIFIED" />)
    expect(screen.getByText('VERIFIED')).toBeInTheDocument()

    rerender(<EvidenceBadge state="TB" />)
    expect(screen.getByText('TB')).toBeInTheDocument()

    rerender(<EvidenceBadge state="SIMULATED" />)
    expect(screen.getByText('SIMULATED')).toBeInTheDocument()
  })

  it('labels a demo value as DEMO and says in its title that it is not from NASA', () => {
    render(<EvidenceBadge state="DEMO" />)

    expect(screen.getByText('DEMO')).toBeInTheDocument()
    expect(screen.getByTitle(/not from NASA/i)).toBeInTheDocument()
  })

  it('labels a value with no verified source as UNVERIFIED', () => {
    render(<EvidenceBadge state="UNVERIFIED" />)

    expect(screen.getByText('UNVERIFIED')).toBeInTheDocument()
  })
})
