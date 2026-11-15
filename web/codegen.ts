import type { CodegenConfig } from '@graphql-codegen/cli'

// Genera tipos desde el contrato. Falla si un documento no valida contra el esquema.
const config: CodegenConfig = {
  schema: '../contracts/schema.graphql',
  documents: ['src/data/graphql/documents/**/*.graphql'],
  generates: {
    'src/data/graphql/generated/': {
      preset: 'client',
      config: { documentMode: 'string' },
    },
  },
}

export default config
