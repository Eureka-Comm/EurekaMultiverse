// src/universe/contracts/Interpretation/InterpretationEngine.ts
/**
 * InterpretationEngine contract.
 * Takes a fully‑typed `UniverseState` and produces a `SceneDescription`.
 * Implementations are free to be async (e.g., loading data) – the
 * interface returns a `Promise` to accomodate that.
 */
import { UniverseState } from "../Semantics/UniverseState";
import { RuntimeContext } from "../Runtime/RuntimeContext";
import { SceneDescription } from "./SceneDescription";

export interface InterpretationEngine {
  /**
   * Produce a scene description from the universe state.
   *
   * @param state   The current `UniverseState` instance.
   * @param context Runtime context (logger, clock, optional event bus).
   * @returns       A `Promise` resolving to a `SceneDescription`.
   */
  interpret(
    state: UniverseState,
    context: RuntimeContext
  ): Promise<SceneDescription>;
}
