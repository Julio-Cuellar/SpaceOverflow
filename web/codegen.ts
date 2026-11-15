import type { CodegenConfig } from '@graphql-codegen/cli'

// Generates types from the contract. Fails if a document does not validate against the schema.
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
