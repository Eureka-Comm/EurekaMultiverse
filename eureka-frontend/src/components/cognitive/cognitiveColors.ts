import type { NodeKind } from '../../domain/cognitiveProjectionGraph';

/**
 * Shared color vocabulary for the cognitive instrument. Every chapter, the
 * Knowledge Map and the ribbon read from these single maps so a given kind /
 * status is visually identical everywhere.
 *
 * LS93 v7 — the per-class Visual Grammar is UNCHANGED (which colour family maps to
 * which class stays the same); only the TONE / SATURATION is lowered into a
 * coherent "scientific instrument" palette (steel-blue, desaturated violet/green/
 * amber) so it reads as a cognitive instrument, not saturated corporate clip-art.
 * These colours double as 3D emissive tones on the dark cognitive surface.
 */
export const NODE_KIND_COLOR: Record<string, string> = {
  PROBLEM: '#3b6ea8',
  EVIDENCE: '#7a6bb8',
  FINDING: '#4a9a63',
  PREDICTION: '#3f8f93',
  PRESCRIPTION: '#4f7fb0',
  ALTERNATIVE: '#4f7fb0',
  DECISION: '#bf7d3b',
  ACTION: '#3f8f93',
  EXECUTION: '#3f8f93',
  RESULT: '#55b97a',
  FROZEN: '#9c7f45',
};

export const NODE_KIND_ORDER: NodeKind[] = [
  'PROBLEM',
  'EVIDENCE',
  'FINDING',
  'PREDICTION',
  'PRESCRIPTION',
  'ALTERNATIVE',
  'DECISION',
  'ACTION',
  'EXECUTION',
  'RESULT',
  'FROZEN',
];

export const STATUS_COLOR: Record<string, string> = {
  VALIDATED: '#1a7f37',
  PYTHON_GOVERNED: '#1a7f37',
  PUBLISHED: '#1a7f37',
  UNSUPPORTED: '#cf222e',
  NOT_EVALUATED: '#b08800',
  HUMAN_AUTHORIZED: '#8250df',
  SELECTED: '#8250df',
  HUMAN_SELECTED: '#8250df',
  SIMULATED: '#0f6e6e',
  FROZEN: '#9a6700',
  PENDING: '#8c959f',
  GOVERNED: '#1a7f37',
  LLM_CANDIDATE: '#0969da',
  CANDIDATE: '#0969da',
  RECOMMENDED: '#0969da',
  grounded: '#1a7f37',
  AVAILABLE: '#1a7f37',
  GAP: '#cf222e',
};

export const EDGE_LABEL_COLOR: Record<string, string> = {
  derived_from: '#8c959f',
  supports: '#0969da',
  produced_by: '#0969da',
  selected_by: '#8250df',
  authorized_by: '#8250df',
  executed_as: '#0f6e6e',
  frozen_as: '#9a6700',
};

export function kindColor(kind: string): string {
  return NODE_KIND_COLOR[kind] || '#0969da';
}

export function statusColor(status: string | null | undefined): string {
  const s = status || 'PENDING';
  return STATUS_COLOR[s] || '#8c959f';
}
