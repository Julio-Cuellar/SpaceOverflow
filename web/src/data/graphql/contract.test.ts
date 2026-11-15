import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { buildSchema, parse, validate, type GraphQLEnumType } from 'graphql'
import { describe, expect, it } from 'vitest'

// Vitest corre con cwd en web/; con jsdom import.meta.url no es una ruta de archivo.
const schemaSource = readFileSync(resolve(process.cwd(), '../contracts/schema.graphql'), 'utf8')
const schema = buildSchema(schemaSource)

const dashboardDocument = readFileSync(
  resolve(process.cwd(), 'src/data/graphql/documents/dashboard.graphql'),
  'utf8',
)

describe('contrato GraphQL (borrador de contracts/schema.graphql)', () => {
  it('the dashboard document validates against the schema', () => {
    expect(validate(schema, parse(dashboardDocument))).toEqual([])
  })

  it('rejects a query for a field that the contract does not define', () => {
    const errors = validate(schema, parse('query { dashboard(habitatId: "h") { noExiste } }'))

    expect(errors.length).toBeGreaterThan(0)
  })

  it('defines the severity enum with the four levels of the interface', () => {
    const severity = schema.getType('Severity') as GraphQLEnumType

    expect(severity.getValues().map((v) => v.name)).toEqual(['NORMAL', 'ATENCION', 'ALERTA', 'CRITICO'])
  })
})
