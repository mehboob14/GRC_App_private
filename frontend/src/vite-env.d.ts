/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "true" enables the in-browser MSW mocks. Anything else (or unset) = real API. */
  readonly VITE_USE_MOCKS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
