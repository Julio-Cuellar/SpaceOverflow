import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SevPill } from './SevPill'

describe('SevPill', () => {
  it('shows the symbol and the text of the level, never only a color', () => {
    render(<SevPill level="CRITICAL" />)

    const pill = screen.getByText('Critical')
    expect(pill).toHaveTextContent('■')
  })

  it('exposes the level as a data attribute for styling and tests', () => {
    const { container } = render(<SevPill level="ATTENTION" />)

    expect(container.firstElementChild).toHaveAttribute('data-severity', 'ATTENTION')
  })
})
