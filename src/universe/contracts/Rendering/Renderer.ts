// src/universe/contracts/Rendering/Renderer.ts
/**
 * Renderer contract – consumes a fully‑resolved `RenderState` and performs
 * the actual drawing (e.g., via Three.js, Canvas, SVG, etc.).
 * Implementations are free to be async; the interface returns a Promise.
 */
import { RenderState } from "./RenderState";
import { RuntimeContext } from "../Runtime/RuntimeContext";

export interface Renderer {
  /**
   * Render the provided `RenderState`.
   *
   * @param state   The state describing what should be rendered.
   * @param context Runtime context (logger, clock, optional event bus).
   */
  render(state: RenderState, context: RuntimeContext): Promise<void>;
}
