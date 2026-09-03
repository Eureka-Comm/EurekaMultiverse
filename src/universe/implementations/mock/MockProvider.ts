// src/universe/implementations/mock/MockProvider.ts
import { UniverseState } from "../../contracts/Semantics/UniverseState";
import { RuntimeContext } from "../../contracts/Runtime/RuntimeContext";
import demoUniverse from "../../fixtures/demo-universe.json";

/**
 * Deterministic provider that returns the fixture content as a UniverseState.
 * No business logic – guarantees reproducibility.
 */
export class MockProvider {
  private readonly universeState: UniverseState;

  constructor(_context?: RuntimeContext) {
    // The JSON import is typed as any; we assert it conforms to UniverseState.
    this.universeState = demoUniverse as UniverseState;
  }

  /** Return the deterministic UniverseState */
  getUniverseState(): UniverseState {
    return this.universeState;
  }
}

// Export a descriptor for registration in the CapabilityRegistry
export const MockProviderDescriptor = {
  id: "mockProvider",
  kind: "provider",
  create: (ctx: RuntimeContext) => new MockProvider(ctx),
};
