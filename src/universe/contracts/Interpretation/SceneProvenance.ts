// src/universe/contracts/Interpretation/SceneProvenance.ts
/**
 * Generic provenance information attached to a `SceneNode`.
 * It points back to the originating semantic objects (entity, phenomenon,
 * relationship) without assuming any particular grammar.
 */
export interface SceneProvenance {
  /** Optional identifier of the originating entity */
  entityId?: string;
  /** Optional identifier of the originating phenomenon */
  phenomenonId?: string;
  /** Optional identifier of the originating relationship */
  relationshipId?: string;
  /** Extensible bag for any additional provenance data */
  extra?: Record<string, unknown>;
}
