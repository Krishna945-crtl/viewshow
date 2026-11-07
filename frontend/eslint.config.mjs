import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // react-three-fiber is imperative by design: we mutate three.js objects inside
    // useFrame/effects every frame. The React Compiler rules read that as a bug.
    files: ["src/components/theatre/**"],
    rules: { "react-hooks/immutability": "off", "react-hooks/purity": "off" },
  },
  {
    // data-fetch-on-mount is intentional (static export, no server components)
    rules: { "react-hooks/set-state-in-effect": "warn" },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "android/**",
    "ios/**",
    "playwright-report/**",
    "test-results/**",
  ]),
]);

export default eslintConfig;
