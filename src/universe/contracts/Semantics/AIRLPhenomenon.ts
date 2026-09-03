// src/universe/contracts/Semantics/AIRLPhenomenon.ts
/**
 * Generic phenomenon definition.
 * Phenomena are domain‑agnostic observations or events that can be
 * interpreted by an InterpretationEngine.
 */
export interface AIRLPhenomenon {
  /** Unique identifier */
  id: string;
  /** Human‑readable name or type */
  name: string;
  /** Optional attributes bag */
  attributes?: Record<string, unknown>;
}
