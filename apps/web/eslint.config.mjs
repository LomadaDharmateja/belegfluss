import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    // Defaults of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Generated from the API's OpenAPI contract (pnpm gen:api):
    "src/api/schema.d.ts",
    // Test output:
    "playwright-report/**",
    "test-results/**",
  ]),
]);

export default eslintConfig;
