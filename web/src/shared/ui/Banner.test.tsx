import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Banner } from './Banner'

describe('Banner', () => {
  it('shows the permanent disclaimer that the prototype is not a medical device', () => {
    render(<Banner />)

    expect(
      screen.getByText('Prototipo de apoyo a la decisión. No es un dispositivo médico'),
    ).toBeInTheDocument()
  })

  it('shows the simulated-data mark', () => {
    render(<Banner />)

    expect(screen.getByText(/Datos simulados/)).toBeInTheDocument()
  })
})
