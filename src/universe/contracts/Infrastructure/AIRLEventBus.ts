// src/universe/contracts/Infrastructure/AIRLEventBus.ts
/**
 * Typed event bus contract for decoupled communication between runtime components.
 * All events carry a `type` string, a timestamp, and a generic payload.
 */
export interface AIRLEvent<T = unknown> {
  /** Event discriminator */
  type: string;
  /** Milliseconds since epoch */
  timestamp: number;
  /** Payload of the event */
  payload: T;
}

/** Unsubscribe function returned by `subscribe` */
export type Unsubscribe = () => void;

/**
 * Event bus interface.
 * Implementations may be synchronous or asynchronous; the contract does not
 * prescribe a delivery model – only that `emit` delivers the event to all
 * current subscribers.
 */
export interface AIRLEventBus {
  /** Emit a typed event to all listeners */
  emit<T>(event: AIRLEvent<T>): void;

  /**
   * Subscribe to events of a specific `type`.
   * The handler receives the fully typed `AIRLEvent` instance.
   * Returns an `Unsubscribe` function to deregister the handler.
   */
  subscribe<T>(
    type: string,
    handler: (event: AIRLEvent<T>) => void
  ): Unsubscribe;
}
