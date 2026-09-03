// src/universe/contracts/Interpretation/SceneDescription.ts
/**
 * High‑level description of a scene produced by an InterpretationEngine.
 * It aggregates `SceneNode`s and optional metadata / edges.
 * The contract is deliberately lightweight – concrete layout strategies
 * may add their own edge types without breaking this core definition.
 */
import { SceneNode } from "./SceneNode";

export interface SceneDescription {
  /** Optional opaque metadata bag for future extensions */
  metadata?: Record<string, unknown>;
  /** The collection of scene nodes */
  nodes: SceneNode[];
  /** Optional edges describing relationships between nodes – can be empty */
  edges?: SceneEdge[];
}

/**
 * Minimal edge definition – left generic to avoid coupling to a specific
 * layout algorithm. Implementations may extend this shape via the
 * `attributes` bag.
 */
export interface SceneEdge {
  /** Source node identifier */
  from: string;
  /** Target node identifier */
  to: string;
  /** Optional attribute bag for edge‑specific data */
  attributes?: Record<string, unknown>;
}
