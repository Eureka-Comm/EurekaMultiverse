// src/universe/contracts/Semantics/AIRLRelationship.ts
/**
 * Generic relationship between two entities.
 * The semantics are left open – concrete grammars can interpret the
 * `type` field as "parent", "orbit", "dependency", etc.
 */
export interface AIRLRelationship {
  /** Identifier of the source entity */
  from: string;
  /** Identifier of the target entity */
  to: string;
  /** Relationship type (free‑form string) */
  type: string;
  /** Optional attributes bag */
  attributes?: Record<string, unknown>;
}
