// src/universe/implementations/mock/MockLayout.ts
import { SceneNode } from "../../contracts/Interpretation/SceneNode";
import { SceneProvenance } from "../../contracts/Interpretation/SceneProvenance";
import { SceneEdge } from "../../contracts/Interpretation/SceneEdge";
import { RenderNode } from "../../contracts/Rendering/RenderNode";
import { RenderEdge } from "../../contracts/Rendering/RenderEdge";
import { RenderState } from "../../contracts/Rendering/RenderState";
import { RuntimeContext } from "../../contracts/Runtime/RuntimeContext";

/**
 * MockLayout copies SceneNode -> RenderNode and SceneEdge -> RenderEdge preserving
 * all fields (id, type, attributes, provenance) and adds a trivial `transform`
 * object (identity). No topology changes.
 */
export class MockLayout {
  constructor(_context?: RuntimeContext) {}

  /** Transform a SceneDescription into a RenderState */
  layout(nodes: SceneNode[], edges: SceneEdge[]): RenderState {
    const renderNodes: RenderNode[] = nodes.map((node) => {
      return {
        id: node.id,
        type: node.type,
        attributes: node.attributes,
        transform: {
          position: { x: 0, y: 0, z: 0 },
        },
        provenance: {
          // copy the whole provenance object from scene node
          ...node.provenance,
        },
      };
    });

    const renderEdges: RenderEdge[] = edges.map((edge) => {
      return {
        id: edge.id,
        sourceId: edge.sourceId,
        targetId: edge.targetId,
        type: edge.type,
        attributes: edge.attributes,
        provenance: {
          ...edge.provenance,
        },
      };
    });

    return { nodes: renderNodes, edges: renderEdges };
  }
}

// Export descriptor for registration
export const MockLayoutDescriptor = {
  id: "mockLayout",
  kind: "layout",
  create: (ctx: RuntimeContext) => new MockLayout(ctx),
};
