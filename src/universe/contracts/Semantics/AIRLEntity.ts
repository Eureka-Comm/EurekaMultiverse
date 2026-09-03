// src/universe/contracts/Semantics/AIRLEntity.ts
/**
 * Generic entity definition used by AIRL.
 * The fields are deliberately minimal and language‑agnostic.
 */
export interface AIRLEntity {
  /** Unique identifier for the entity */
  id: string;
  /** Kind or type of the entity (e.g., "galaxy", "planet", "customer") */
  kind: string;
  /** Optional domain namespace, useful for disambiguation */
  domain?: string;
  /** Arbitrary attribute bag – concrete grammars can store any extra data here */
  attributes: Record<string, unknown>;
}
