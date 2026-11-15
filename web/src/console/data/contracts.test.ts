import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { buildSchema, parse, validate } from "graphql";
import { describe, expect, it } from "vitest";
import { queryDocuments, mutations } from "./operations";
const exported = resolve(
  process.cwd(),
  "../contracts/schema.generated.graphql",
);
const target = resolve(
  process.cwd(),
  "../contracts/frontend-integration.graphql",
);
const actual = existsSync(exported);
const schema = buildSchema(readFileSync(actual ? exported : target, "utf8"));
describe(
  actual
    ? "Dev A exported GraphQL contract"
    : "Frontend integration target (backend export absent)",
  () => {
    it.each([...queryDocuments, ...Object.values(mutations)])(
      "validates operation %# against the selected schema",
      (document) => {
        expect(validate(schema, parse(document)).map((e) => e.message)).toEqual(
          [],
        );
      },
    );
    it("requires the backend export when running the merge gate", () => {
      if (process.env.SPACEAPP_REQUIRE_BACKEND_SCHEMA === "1")
        expect(
          actual,
          "Export Dev A’s schema before marking integration complete",
        ).toBe(true);
    });
  },
);
