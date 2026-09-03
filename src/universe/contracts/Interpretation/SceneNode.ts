// src/universe/contracts/Interpretation/SceneNode.ts
/**
 * A node in the abstract scene graph produced by an InterpretationEngine.
 * It contains only semantic‑level information; layout‑specific data (e.g.
 * positions) are handled later by a LayoutStrategy.
 */
import { SceneProvenance } from "./SceneProvenance";

export interface SceneNode {
  /** Unique identifier for the node within the scene */
  id: string;
  /** Abstract type of the node (e.g., "galaxy", "planet", "point") */
  type: string;
  /** Arbitrary attribute bag – concrete grammars may store any data */
  attributes: Record<string, unknown>;
  /** Optional visual hints that may guide layout/renderer (radius, colour, …) */
  visualHints?: {
    radius?: number;
    color?: string;
  };
  /** Provenance linking the node back to its source semantic objects */
  provenance: SceneProvenance;
}
