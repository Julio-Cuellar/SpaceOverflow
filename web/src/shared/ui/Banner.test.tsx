import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Banner } from './Banner'

describe('Banner', () => {
  it('shows the permanent disclaimer that the prototype is not a medical device', () => {
    render(<Banner />)

    expect(
      screen.getByText('Decision-support prototype. Not a medical device.'),
    ).toBeInTheDocument()
  })

  it('shows the simulated-data mark', () => {
    render(<Banner />)

    expect(screen.getByText(/Simulated data/)).toBeInTheDocument()
  })
})
