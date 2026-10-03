import { globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const config = [
  ...nextVitals,
  ...nextTs,
  globalIgnores([".next/**", "out/**", "next-env.d.ts", ".npm-cache/**"]),
  {
    // Static export with unoptimised images: plain <img> with explicit width and height is the intended path.
    rules: { "@next/next/no-img-element": "off" },
  },
];

export default config;
