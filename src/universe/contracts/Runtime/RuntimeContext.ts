// src/universe/contracts/Runtime/RuntimeContext.ts
/**
 * Minimal runtime context. Provides optional logger, clock and event bus.
 */
export interface RuntimeContext {
  /** Optional logging facility */
  logger?: Logger;
  /** Optional clock for time‑based operations */
  clock?: Clock;
  /** Optional event bus for decoupled communication */
  eventBus?: AIRLEventBus;
}

// Simple logger and clock abstractions (can be expanded later)
export interface Logger {
  log(message: string): void;
  error(message: string): void;
}

export interface Clock {
  now(): Date;
}

// Forward declaration for the event bus contract (avoids circular imports)
export interface AIRLEventBus {}
