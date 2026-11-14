import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EvidenceBadge } from './EvidenceBadge'

describe('EvidenceBadge', () => {
  it('labels each evidence state with its own text', () => {
    const { rerender } = render(<EvidenceBadge state="VERIFICADO" />)
    expect(screen.getByText('VERIFICADO')).toBeInTheDocument()

    rerender(<EvidenceBadge state="TB" />)
    expect(screen.getByText('TB')).toBeInTheDocument()

    rerender(<EvidenceBadge state="SIMULADO" />)
    expect(screen.getByText('SIMULADO')).toBeInTheDocument()
  })

  it('labels a demo value as DEMO and says in its title that it is not from NASA', () => {
    render(<EvidenceBadge state="DEMO" />)

    expect(screen.getByText('DEMO')).toBeInTheDocument()
    expect(screen.getByTitle(/no es de NASA/i)).toBeInTheDocument()
  })

  it('labels a value with no verified source as NO VERIFICADO', () => {
    render(<EvidenceBadge state="NO_VERIFICADO" />)

    expect(screen.getByText('NO VERIFICADO')).toBeInTheDocument()
  })
})
