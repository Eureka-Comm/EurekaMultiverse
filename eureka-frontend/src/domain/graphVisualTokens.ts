// CONSTELACIÓN — single source of node-kind visual tokens (color + label).
// The graph renderer, the Control Deck's VIEW LAYERS, and the LEGEND all read from here so the
// color language is consistent and never duplicated. Presentation-only; no authority, no data.
import type { NodeKind } from './cognitiveProjectionGraph';

export const NODE_KIND_ORDER: NodeKind[] = [
  'PROBLEM', 'EVIDENCE', 'FINDING', 'PREDICTION', 'PRESCRIPTION', 'ALTERNATIVE',
  'DECISION', 'ACTION', 'EXECUTION', 'RESULT', 'FROZEN',
];

/** Base fill color per kind (matches the CONSTELACIÓN semantic language). */
export const NODE_KIND_COLOR: Record<NodeKind, string> = {
  PROBLEM: '#29e0ff',
  EVIDENCE: '#29e0ff',
  FINDING: '#7b61ff',
  PREDICTION: '#29e0ff',
  PRESCRIPTION: '#7b61ff',
  ALTERNATIVE: '#ff6ad5',
  DECISION: '#ff3d8c',
  ACTION: '#ff7a3c',
  EXECUTION: '#4dff9d',
  RESULT: '#4dff9d',
  FROZEN: '#9b6bff',
};

/** Human label per kind (VIEW LAYERS chips + LEGEND). */
export const NODE_KIND_LABEL: Record<NodeKind, string> = {
  PROBLEM: 'Problem',
  EVIDENCE: 'Evidence',
  FINDING: 'Findings',
  PREDICTION: 'Predictions',
  PRESCRIPTION: 'Prescription',
  ALTERNATIVE: 'Options',
  DECISION: 'Decision',
  ACTION: 'Action',
  EXECUTION: 'Execution',
  RESULT: 'Result',
  FROZEN: 'Frozen',
};

/** The kinds exposed by the FOCUS FILTER (All + this subset). */
export const FOCUS_KINDS: NodeKind[] = ['DECISION', 'ACTION', 'EXECUTION', 'RESULT', 'FROZEN'];

export function nodeKindColor(kind: NodeKind): string {
  return NODE_KIND_COLOR[kind] ?? '#d9c8ff';
}
