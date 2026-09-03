// src/universe/implementations/mock/MockEventBus.ts
import { AIRLEvent, AIRLEventBus, Unsubscribe } from "../../contracts/Infrastructure/AIRLEventBus";

/**
 * Simple in‑memory event bus used by the mock implementations.
 * Supports synchronous delivery and basic subscription management.
 */
export class MockEventBus implements AIRLEventBus {
  private readonly subscribers: Map<string, Set<(event: AIRLEvent<any>) => void>> = new Map();

  emit<T>(event: AIRLEvent<T>): void {
    const handlers = this.subscribers.get(event.type);
    if (handlers) {
      for (const h of Array.from(handlers)) {
        h(event);
      }
    }
  }

  subscribe<T>(type: string, handler: (event: AIRLEvent<T>) => void): Unsubscribe {
    let set = this.subscribers.get(type);
    if (!set) {
      set = new Set();
      this.subscribers.set(type, set);
    }
    set.add(handler as (event: AIRLEvent<any>) => void);
    return () => {
      const s = this.subscribers.get(type);
      if (s) s.delete(handler as (event: AIRLEvent<any>) => void);
    };
  }
}
