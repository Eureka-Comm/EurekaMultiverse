// src/universe/contracts/Semantics/UniverseMetadata.ts
/**
 * Minimal metadata for a universe. Extend as needed.
 */
export interface UniverseMetadata {
  /** Semantic version of the universe definition */
  version: string;
  /** Identifier of the grammar or schema used */
  grammar: string;
  /** ISO‑8601 creation timestamp */
  createdAt: string;
  /** Optional source identifier (e.g., file, URL) */
  source?: string;
}
