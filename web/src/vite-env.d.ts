/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Optional base URL of the API. Public by design: never put a secret in any VITE_* value. */
  readonly VITE_API_URL?: string;
  /** Optional folder holding the data files (default: /data/panama-2026). */
  readonly VITE_DATA_URL?: string;
  /** Optional public URL of the code repository, shown in the About window. */
  readonly VITE_REPO_URL?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
