// src/universe/implementations/mock/MockRenderer.ts
import { RenderState } from "../../contracts/Rendering/RenderState";
import { RuntimeContext } from "../../contracts/Runtime/RuntimeContext";
import { AIRLEventBus } from "../../contracts/Infrastructure/AIRLEventBus";
import { AIRLEvent } from "../../contracts/Infrastructure/AIRLEventBus";

/**
 * MockRenderer records the RenderState it receives, counts renders, timestamps the
 * last render and emits a `renderComplete` event via the AIRLEventBus.
 */
export class MockRenderer {
  private readonly eventBus: AIRLEventBus;
  public renderCount = 0;
  public lastState: RenderState | null = null;
  public lastTimestamp: Date | null = null;

  constructor(_context?: RuntimeContext) {
    // In a real runtime, the context would provide the event bus; here we create a new one.
    this.eventBus = new AIRLEventBus();
  }

  /** Render the provided state (passive – just stores it). */
  render(state: RenderState): void {
    this.renderCount++;
    this.lastState = state;
    this.lastTimestamp = new Date();
    const event: AIRLEvent<RenderState> = {
      type: "renderComplete",
      timestamp: this.lastTimestamp,
      payload: state,
    };
    this.eventBus.emit(event);
  }

  /** Expose the bus for external listeners (e.g., tests). */
  getEventBus(): AIRLEventBus {
    return this.eventBus;
  }
}

// Export descriptor for registration
export const MockRendererDescriptor = {
  id: "mockRenderer",
  kind: "renderer",
  create: (ctx: RuntimeContext) => new MockRenderer(ctx),
};
