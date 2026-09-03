// src/universe/contracts/CONTRACT_VERSION.ts
/**
 * Centralised contract version identifiers.
 * Used to detect incompatibilities between runtime components and
 * providers/grammars without inspecting TypeScript types.
 */
export const CONTRACT_VERSION = {
  UniverseState: "1.0.0",
  SceneDescription: "1.0.0",
  RenderState: "1.0.0",
} as const;
