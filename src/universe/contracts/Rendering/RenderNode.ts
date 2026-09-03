// src/universe/contracts/Rendering/RenderNode.ts
/**
 * RenderNode contract – a concrete, layout‑aware representation of a scene element.
 * It contains rendering‑specific attributes (e.g., transform) and optional provenance
 * linking back to the originating `SceneNode` or semantic objects.
 */
export interface RenderNode {
  /** Unique identifier for the node within the render state */
  id: string;
  /** Abstract type – typically mirrors the `SceneNode.type` */
  type: string;
  /** Arbitrary attribute bag for renderer‑specific data */
  attributes: Record<string, unknown>;
  /** Optional transform data produced by a LayoutStrategy */
  transform?: {
    position?: { x: number; y: number; z: number };
    rotation?: { x: number; y: number; z: number };
    scale?: { x: number; y: number; z: number };
  };
  /** Optional provenance that can be used to trace back to source objects */
  provenance?: Record<string, unknown>;
}
