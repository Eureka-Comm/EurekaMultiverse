// src/universe/contracts/Interpretation/SceneEdge.ts
/**
 * Edge representation in the abstract scene graph.
 * Mirrors a relationship from `UniverseState`.
 */
export interface SceneEdge {
  /** Unique identifier for the edge */
  id: string;
  /** Source node identifier */
  sourceId: string;
  /** Target node identifier */
  targetId: string;
  /** Type of relationship (e.g., "orbits") */
  type: string;
  /** Arbitrary attribute bag */
  attributes: Record<string, unknown>;
  /** Provenance linking back to original relationship */
  provenance: {
    relationshipId?: string;
    extra?: Record<string, unknown>;
  };
}
