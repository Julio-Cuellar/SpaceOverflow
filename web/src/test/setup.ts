import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Vitest no expone globals aquí, así que Testing Library no limpia el DOM solo.
afterEach(() => {
  cleanup()
})
