// src/universe/contracts/Infrastructure/CapabilityRegistry.ts
/**
 * Generic capability descriptor used by the `CapabilityRegistry`.
 * The `kind` field indicates the category of capability (e.g., "interpreter",
 * "layout", "renderer"). The `id` uniquely identifies a concrete implementation
 * within that category. The `create` factory receives a `RuntimeContext` and
 * returns an instance of the capability.
 */
export interface CapabilityDescriptor<T> {
  /** Unique identifier for this capability implementation */
  id: string;
  /** Category of the capability (e.g., "interpreter", "layout", "renderer") */
  kind: string;
  /** Factory that creates an instance given a runtime context */
  create(context: RuntimeContext): T;
}

import { RuntimeContext } from "../Runtime/RuntimeContext";

/**
 * Passive, descriptor‑based registry for capability factories.
 *
 * - `register` stores a descriptor without instantiating anything.
 * - `resolve` lazily creates the capability instance on request.
 *
 * The registry is deliberately agnostic of concrete capability types; callers
 * provide the generic type parameter `T` that matches the expected capability.
 */
export class CapabilityRegistry {
  /** Internal map keyed by `${kind}:${id}` */
  private readonly descriptors = new Map<string, CapabilityDescriptor<unknown>>();

  /** Register a capability descriptor */
  register<T>(descriptor: CapabilityDescriptor<T>): void {
    const key = `${descriptor.kind}:${descriptor.id}`;
    if (this.descriptors.has(key)) {
      throw new Error(`Capability already registered for ${key}`);
    }
    this.descriptors.set(key, descriptor as CapabilityDescriptor<unknown>);
  }

  /** Resolve (instantiate) a capability by its kind and id */
  resolve<T>(kind: string, id: string, context: RuntimeContext): T {
    const key = `${kind}:${id}`;
    const descriptor = this.descriptors.get(key) as CapabilityDescriptor<T> | undefined;
    if (!descriptor) {
      throw new Error(`Capability not found for ${key}`);
    }
    return descriptor.create(context);
  }

  /** Optional helper to list all registered capability keys (useful for debugging) */
  list(): string[] {
    return Array.from(this.descriptors.keys());
  }
}
