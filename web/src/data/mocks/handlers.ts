import { graphql, HttpResponse } from 'msw'
import { dashboardFixture } from './fixtures'

/** MSW handlers for the GraphQL operations the interface uses without a backend. */
export const handlers = [
  graphql.query('Dashboard', () =>
    HttpResponse.json({ data: { dashboard: dashboardFixture('normal') } }),
  ),
]
