import { graphql, HttpResponse } from 'msw'
import { dashboardFixture } from './fixtures'

/** Handlers MSW para las operaciones GraphQL que la interfaz usa sin backend. */
export const handlers = [
  graphql.query('Dashboard', () =>
    HttpResponse.json({ data: { dashboard: dashboardFixture('normal') } }),
  ),
]
