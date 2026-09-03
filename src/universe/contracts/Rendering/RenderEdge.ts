// src/universe/contracts/Rendering/RenderEdge.ts
/**
 * Minimal edge definition for the render graph.
 * Mirrors `SceneEdge` but lives in the render layer, allowing layout or
 * renderer specific attributes without coupling to the interpretation layer.
 */
export interface RenderEdge {
  /** Source node identifier */
  from: string;
  /** Target node identifier */
  to: string;
  /** Optional attribute bag for edge‑specific render data */
  attributes?: Record<string, unknown>;
}
