import { z } from 'zod';
import { CanonicalWorkStateSchema } from './src/domain/canonicalSchema.js';

const staleState = {
  work: {
    workId: '123',
    taskCategory: 'BUSINESS',
    status: 'READY',
    userIntent: 'Do something'
  },
  resolved_pipeline: ['EM[A]', 'EM[B]'],
  state: {
    acfl: { weights: {}, criteria: [], alternatives: [], normalized_scores: {}, frontier: [], sensitivity: {} },
    feasible_only: false,
    result: null
  },
  visualizations: [],
  available_capabilities: [],
  gaps: [],
  conditions: [],
  tool_call_id: null,
  revision: 1,
  extracted_entities: {}
};

try {
  CanonicalWorkStateSchema.parse(staleState);
  console.log("FAIL: Stale state was accepted!");
} catch (e: any) {
  if (e instanceof z.ZodError) {
    console.log("PASS: Stale state rejected with error:", e.errors.map(err => err.message).join(', '));
  } else {
    console.log("PASS: Stale state rejected:", e.message);
  }
}

const missingFieldState = {
  work: {
    workId: '123',
    taskCategory: 'BUSINESS',
    status: 'READY',
    userIntent: 'Do something'
  },
  execution_plan: { steps: [] },
  state: {
    acfl: { weights: {}, criteria: [], alternatives: [], normalized_scores: {}, frontier: [], sensitivity: {} },
    feasible_only: false,
    result: null
  },
  visualizations: [],
  available_capabilities: [],
  gaps: [],
  // missing 'conditions'
  tool_call_id: null,
  revision: 1,
  extracted_entities: {}
};

try {
  CanonicalWorkStateSchema.parse(missingFieldState);
  console.log("FAIL: Missing field state was accepted!");
} catch (e: any) {
  if (e instanceof z.ZodError) {
    console.log("PASS: Missing field state rejected with error:", e.errors.map(err => err.message).join(', '));
  } else {
    console.log("PASS: Missing field state rejected:", e.message);
  }
}
