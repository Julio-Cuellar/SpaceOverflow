import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

const server = setupServer(...handlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

const DASHBOARD = `query Dashboard($habitatId: ID!) {
  dashboard(habitatId: $habitatId) { habitatId globalSeverity vitals { key label value unit domain severity evidenceState origin } }
}`

describe('mock GraphQL (MSW)', () => {
  it('answers the Dashboard query with the example dashboard', async () => {
    const response = await fetch('http://localhost/graphql', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ query: DASHBOARD, variables: { habitatId: 'hab-01' } }),
    })
    const body = (await response.json()) as { data: { dashboard: { globalSeverity: string; vitals: unknown[] } } }

    expect(response.status).toBe(200)
    expect(body.data.dashboard.globalSeverity).toBe('NORMAL')
    expect(body.data.dashboard.vitals.length).toBeGreaterThan(0)
  })
})
