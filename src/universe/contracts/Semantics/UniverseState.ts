// src/universe/contracts/Semantics/UniverseState.ts
/**
 * Central contract describing the analytical knowledge about a universe.
 * It composes the minimal semantic primitives defined in this package.
 */
import { UniverseMetadata } from "./UniverseMetadata";
import { AIRLEntity } from "./AIRLEntity";
import { AIRLRelationship } from "./AIRLRelationship";
import { AIRLPhenomenon } from "./AIRLPhenomenon";

export interface UniverseState {
  /** Universe‑wide metadata */
  metadata: UniverseMetadata;
  /** Collection of entities present in the universe */
  entities: AIRLEntity[];
  /** Relationships between entities */
  relationships: AIRLRelationship[];
  /** Observed or derived phenomena */
  phenomena: AIRLPhenomenon[];
}
