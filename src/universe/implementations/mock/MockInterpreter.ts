// src/universe/implementations/mock/MockInterpreter.ts
import { UniverseState } from "../../contracts/Semantics/UniverseState";
import { SceneNode } from "../../contracts/Interpretation/SceneNode";
import { SceneProvenance } from "../../contracts/Interpretation/SceneProvenance";
import { SceneDescription } from "../../contracts/Interpretation/SceneDescription";
import { SceneEdge } from "../../contracts/Interpretation/SceneEdge";
import { RuntimeContext } from "../../contracts/Runtime/RuntimeContext";

/**
 * MockInterpreter converts each entity in a UniverseState into a SceneNode (1:1)
 * and each relationship into a SceneEdge (1:1). No additional logic – fully
 * deterministic.
 */
export class MockInterpreter {
  constructor(_context?: RuntimeContext) {}

  /** Transform a UniverseState into a SceneDescription */
  interpret(state: UniverseState): SceneDescription {
    const nodes: SceneNode[] = state.entities.map((entity) => {
      const provenance: SceneProvenance = { entityId: entity.id };
      return {
        id: entity.id,
        type: entity.type,
        attributes: entity.attributes ?? {},
        visualHints: {},
        provenance,
      };
    });

    const edges: SceneEdge[] = (state.relationships ?? []).map((rel) => {
      const provenance: SceneProvenance = {
        relationshipId: `${rel.source}-${rel.target}`,
      };
      return {
        id: `${rel.source}-${rel.target}`,
        sourceId: rel.source,
        targetId: rel.target,
        type: rel.type,
        attributes: rel.attributes ?? {},
        provenance,
      };
    });

    return { nodes, edges };
  }
}

// Export descriptor for registration
export const MockInterpreterDescriptor = {
  id: "mockInterpreter",
  kind: "interpreter",
  create: (ctx: RuntimeContext) => new MockInterpreter(ctx),
};
