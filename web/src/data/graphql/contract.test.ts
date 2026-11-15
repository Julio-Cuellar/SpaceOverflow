import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { buildSchema, parse, validate, type GraphQLEnumType } from 'graphql'
import { describe, expect, it } from 'vitest'

// Vitest runs with cwd in web/; under jsdom import.meta.url is not a file path.
const schemaSource = readFileSync(resolve(process.cwd(), '../contracts/schema.graphql'), 'utf8')
const schema = buildSchema(schemaSource)

const dashboardDocument = readFileSync(
  resolve(process.cwd(), 'src/data/graphql/documents/dashboard.graphql'),
  'utf8',
)

describe('GraphQL contract (draft of contracts/schema.graphql)', () => {
  it('the dashboard document validates against the schema', () => {
    expect(validate(schema, parse(dashboardDocument))).toEqual([])
  })

  it('rejects a query for a field that the contract does not define', () => {
    const errors = validate(schema, parse('query { dashboard(habitatId: "h") { doesNotExist } }'))

    expect(errors.length).toBeGreaterThan(0)
  })

  it('defines the severity enum with the four levels of the interface', () => {
    const severity = schema.getType('Severity') as GraphQLEnumType

    expect(severity.getValues().map((v) => v.name)).toEqual(['NORMAL', 'ATTENTION', 'ALERT', 'CRITICAL'])
  })
})
