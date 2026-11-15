import { existsSync } from "node:fs";
import type { CodegenConfig } from "@graphql-codegen/cli";

// The exported backend schema wins. The target only enables development before Dev A merges.
const exported = "../contracts/schema.generated.graphql";
const config: CodegenConfig = {
  schema: existsSync(exported)
    ? exported
    : "../contracts/frontend-integration.graphql",
  documents: [
    "src/data/graphql/documents/**/*.graphql",
    "src/console/data/operations.graphql",
  ],
  generates: {
    "src/data/graphql/generated/": {
      preset: "client",
      config: { documentMode: "string" },
    },
  },
};
export default config;
