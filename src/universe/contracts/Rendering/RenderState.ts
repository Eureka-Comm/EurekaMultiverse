// src/universe/contracts/Rendering/RenderState.ts
/**
 * RenderState contract – the output of a LayoutStrategy that is consumed by a Renderer.
 * It mirrors the structure of `SceneDescription` but is intended for a concrete
 * layout (positions, transforms, etc.) and may contain additional rendering‑specific
 * attributes.
 */
import { RenderNode } from "./RenderNode";
import { RenderEdge } from "./RenderEdge";

export interface RenderState {
  /** Optional opaque metadata bag for renderer extensions */
  metadata?: Record<string, unknown>;
  /** Collection of renderable nodes */
  nodes: RenderNode[];
  /** Optional edges linking nodes – can be empty */
  edges?: RenderEdge[];
}
