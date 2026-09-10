import type { GraphArtifact, GraphEdge } from '../../domain/cognitiveProjectionGraph';

/**
 * constellationNav — PURE presentation/interaction math for the Constellation.
 * Zoom/pan operate ONLY on the SVG `viewBox` (presentation state). This never touches
 * the CognitiveProjectionGraph (data), never fabricates nodes/edges, and is unit-testable
 * without a DOM. Selection/trace follow REAL graph edges (no invented relationships).
 */

/** SVG width/height (content coordinate space of the galaxy). */
export const GALAXY_W = 1440;
export const GALAXY_H = 900;
export const GALAXY_CX = GALAXY_W / 2;
export const GALAXY_CY = GALAXY_H / 2 - 10;

export const MIN_SCALE = 0.6; // zoom-out floor
export const MAX_SCALE = 3.2; // zoom-in ceiling

/** SVG viewBox = visible window into the content space. */
export interface ViewportBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export function baseBox(): ViewportBox {
  return { x: 0, y: 0, w: GALAXY_W, h: GALAXY_H };
}

/** Content scale implied by a viewBox (1 = full galaxy). */
export function viewportScale(vb: ViewportBox): number {
  return GALAXY_W / vb.w;
}

function clamp(v: number, lo: number, hi: number) {
  if (!Number.isFinite(v)) return lo;
  return Math.min(hi, Math.max(lo, v));
}

/** Clamp a viewBox so the galactic core (GALAXY_CX, GALAXY_CY) stays on-screen — the
 *  galaxy can never be permanently panned/zoomed away. */
function clampBox(vb: ViewportBox): ViewportBox {
  const w = clamp(vb.w, GALAXY_W / MAX_SCALE, GALAXY_W / MIN_SCALE);
  const h = w * (GALAXY_H / GALAXY_W);
  const x = clamp(vb.x, GALAXY_CX - w, GALAXY_CX);
  const y = clamp(vb.y, GALAXY_CY - h, GALAXY_CY);
  return { x, y, w, h };
}

/**
 * Zoom by factor `f` (f > 1 = zoom in / content larger) keeping the content point
 * (u, v) — given in content coordinates — fixed on screen. `u`/`v` are the content
 * coordinates under the pointer (or the centre when clicking the zoom buttons).
 */
export function zoomViewport(vb: ViewportBox, u: number, v: number, f: number): ViewportBox {
  if (!Number.isFinite(f) || f <= 0) return vb;
  const nw = clamp(vb.w / f, GALAXY_W / MAX_SCALE, GALAXY_W / MIN_SCALE);
  const nh = nw * (GALAXY_H / GALAXY_W);
  const fracU = (u - vb.x) / vb.w;
  const fracV = (v - vb.y) / vb.h;
  const nx = u - fracU * nw;
  const ny = v - fracV * nh;
  return clampBox({ x: nx, y: ny, w: nw, h: nh });
}

/**
 * Pan by a delta expressed in content units. Dragging right (dxContent > 0) moves the
 * content right, revealing the left side, so the viewBox origin shifts left.
 */
export function panViewport(vb: ViewportBox, dxContent: number, dyContent: number): ViewportBox {
  return clampBox({ x: vb.x - dxContent, y: vb.y - dyContent, w: vb.w, h: vb.h });
}

/** EUREKA cognitive pipeline stage order (matches the provenance narrative). */
const PIPELINE_ORDER: Record<string, number> = {
  PROBLEM: 0, EVIDENCE: 1, FINDING: 2, PREDICTION: 3, PRESCRIPTION: 4,
  ALTERNATIVE: 5, DECISION: 6, ACTION: 7, EXECUTION: 8, RESULT: 9, FROZEN: 10,
};

/** Stage rank for a NodeKind (unknown kinds are treated as neutral/-1). */
export function kindRank(kind: string): number {
  return PIPELINE_ORDER[kind] ?? -1;
}

function adjacency(edges: GraphEdge[]): Map<string, string[]> {
  const adj = new Map<string, string[]>();
  for (const e of edges) {
    if (!adj.has(e.source)) adj.set(e.source, []);
    if (!adj.has(e.target)) adj.set(e.target, []);
    adj.get(e.source)!.push(e.target);
    adj.get(e.target)!.push(e.source);
  }
  return adj;
}

/**
 * Transitive UPSTREAM closure (toward EVIDENCE/root), following ONLY real edges.
 * Direction = cognitive pipeline stage order (lower stage = upstream). Stops where
 * no real edge leads to an earlier stage. Never invents connections.
 */
export function upstreamClosure(id: string, edges: GraphEdge[], nodes: GraphArtifact[]): Set<string> {
  const rank = new Map(nodes.map((n) => [n.id, kindRank(n.kind)]));
  const me = rank.get(id);
  if (me == null) return new Set<string>([id]);
  const adj = adjacency(edges);
  const out = new Set<string>([id]);
  const q = [id];
  while (q.length) {
    const cur = q.shift()!;
    const cr = rank.get(cur);
    if (cr == null) continue;
    for (const nb of adj.get(cur) ?? []) {
      const nr = rank.get(nb);
      if (nr != null && nr < cr && !out.has(nb)) { out.add(nb); q.push(nb); }
    }
  }
  return out;
}

/**
 * Transitive DOWNSTREAM closure (toward FROZEN/result), following ONLY real edges.
 * Direction = higher pipeline stage. Stops where no real edge leads forward.
 */
export function downstreamClosure(id: string, edges: GraphEdge[], nodes: GraphArtifact[]): Set<string> {
  const rank = new Map(nodes.map((n) => [n.id, kindRank(n.kind)]));
  const me = rank.get(id);
  if (me == null) return new Set<string>([id]);
  const adj = adjacency(edges);
  const out = new Set<string>([id]);
  const q = [id];
  while (q.length) {
    const cur = q.shift()!;
    const cr = rank.get(cur);
    if (cr == null) continue;
    for (const nb of adj.get(cur) ?? []) {
      const nr = rank.get(nb);
      if (nr != null && nr > cr && !out.has(nb)) { out.add(nb); q.push(nb); }
    }
  }
  return out;
}

/** Ordered upstream chain (earliest-stage-first traversal, seed excluded). */
export function upstreamChain(id: string, edges: GraphEdge[], nodes: GraphArtifact[]): string[] {
  const rank = new Map(nodes.map((n) => [n.id, kindRank(n.kind)]));
  const me = rank.get(id);
  if (me == null) return [];
  const adj = adjacency(edges);
  const seen = new Set<string>([id]);
  const order: string[] = [];
  const q = [id];
  while (q.length) {
    const cur = q.shift()!;
    const cr = rank.get(cur);
    if (cr == null) continue;
    for (const nb of adj.get(cur) ?? []) {
      const nr = rank.get(nb);
      if (nr != null && nr < cr && !seen.has(nb)) { seen.add(nb); order.push(nb); q.push(nb); }
    }
  }
  return order;
}

/** Ordered downstream chain (later-stage-first traversal, seed excluded). */
export function downstreamChain(id: string, edges: GraphEdge[], nodes: GraphArtifact[]): string[] {
  const rank = new Map(nodes.map((n) => [n.id, kindRank(n.kind)]));
  const me = rank.get(id);
  if (me == null) return [];
  const adj = adjacency(edges);
  const seen = new Set<string>([id]);
  const order: string[] = [];
  const q = [id];
  while (q.length) {
    const cur = q.shift()!;
    const cr = rank.get(cur);
    if (cr == null) continue;
    for (const nb of adj.get(cur) ?? []) {
      const nr = rank.get(nb);
      if (nr != null && nr > cr && !seen.has(nb)) { seen.add(nb); order.push(nb); q.push(nb); }
    }
  }
  return order;
}

/** Rough status category used to pick a semantic (non-arbitrary) accent. */
export type StatusTone = 'governed' | 'validated' | 'pending' | 'waiting' | 'gap' | 'frozen' | 'neutral';export function statusTone(status: string): StatusTone {
  const s = (status || '').toUpperCase();
  if (!s) return 'neutral';
  if (/WAITING_FOR_HUMAN_INPUT|HUMAN_SELECTED/.test(s)) return 'waiting';
  if (/NOT_EVALUATED|NOT_APPLICABLE|DATA NOT AVAILABLE|UNSUPPORTED/.test(s)) return 'gap';
  if (/FROZEN/.test(s)) return 'frozen';
  if (/VALIDATED|COMPLETED|PUBLISHED|EVALUATED|EXECUTED/.test(s)) return 'validated';
  if (/GOVERNED|GROUNDED|DERIVED/.test(s)) return 'governed';
  if (/PENDING|RECOMMENDED|CANDIDATE/.test(s)) return 'pending';
  return 'neutral';
}

/** Semantic zoom level (0 = FAR, 1 = MEDIUM, 2 = CLOSE) from the effective scale. */
export type SemanticLevel = 0 | 1 | 2;
export function semanticLevel(scale: number): SemanticLevel {
  if (scale >= 2.0) return 2; // CLOSE — description / EM / authority
  if (scale >= 1.25) return 1; // MEDIUM — + status
  return 0; // FAR — kind + id
}

/** Edge ids incident to a node (selection neighborhood focus). */
export function edgesTouching(id: string, edges: GraphEdge[]): Set<string> {
  const out = new Set<string>();
  for (const e of edges) {
    if (e.source === id || e.target === id) out.add(e.id);
  }
  return out;
}

/** Direct upstream neighbor ids (1 hop toward an earlier pipeline stage), using REAL edges. */
export function directUpstreamIds(id: string, edges: GraphEdge[], nodes: GraphArtifact[]): string[] {
  const rank = new Map(nodes.map((n) => [n.id, kindRank(n.kind)]));
  const me = rank.get(id);
  if (me == null) return [];
  const out = new Set<string>();
  for (const e of edges) {
    if (e.target === id && rank.get(e.source) != null && (rank.get(e.source) as number) < me) out.add(e.source);
    if (e.source === id && rank.get(e.target) != null && (rank.get(e.target) as number) < me) out.add(e.target);
  }
  return [...out];
}

/** Direct downstream neighbor ids (1 hop toward a later pipeline stage), using REAL edges. */
export function directDownstreamIds(id: string, edges: GraphEdge[], nodes: GraphArtifact[]): string[] {
  const rank = new Map(nodes.map((n) => [n.id, kindRank(n.kind)]));
  const me = rank.get(id);
  if (me == null) return [];
  const out = new Set<string>();
  for (const e of edges) {
    if (e.target === id && rank.get(e.source) != null && (rank.get(e.source) as number) > me) out.add(e.source);
    if (e.source === id && rank.get(e.target) != null && (rank.get(e.target) as number) > me) out.add(e.target);
  }
  return [...out];
}

/** Edge ids with BOTH endpoints inside a node set (trace-chain emphasis). */
export function edgesWithin(set: Set<string>, edges: GraphEdge[]): Set<string> {
  const out = new Set<string>();
  for (const e of edges) {
    if (set.has(e.source) && set.has(e.target)) out.add(e.id);
  }
  return out;
}

/** Honest gap statuses (states that mean "open / not yet established"). */
const GAP_RE = /NOT_EVALUATED|UNSUPPORTED|DATA NOT AVAILABLE|NOT_APPLICABLE|WAITING_FOR_HUMAN_INPUT/i;
export function isGapStatus(status: string): boolean {
  return !!status && GAP_RE.test(status);
}

/** Ids of real nodes whose status is a gap (never synthesized). */
export function gapNodeIds(nodes: GraphArtifact[]): string[] {
  return nodes.filter((n) => isGapStatus(n.status)).map((n) => n.id);
}

/** Cognitive stages for the state bar (representation, not an executable workflow). */
export const COGNITIVE_STAGES: { kind: string; label: string }[] = [
  { kind: 'PROBLEM', label: 'PROBLEM' },
  { kind: 'EVIDENCE', label: 'EVIDENCE' },
  { kind: 'FINDING', label: 'FINDINGS' },
  { kind: 'PREDICTION', label: 'PREDICTIONS' },
  { kind: 'PRESCRIPTION', label: 'OPTIONS' },
  { kind: 'ALTERNATIVE', label: 'OPTIONS' },
  { kind: 'DECISION', label: 'DECISION' },
  { kind: 'ACTION', label: 'ACTION' },
  { kind: 'EXECUTION', label: 'EXECUTION' },
  { kind: 'RESULT', label: 'RESULT' },
  { kind: 'FROZEN', label: 'FROZEN' },
];

/** Real counts of nodes per stage kind (0 when absent — never invent an object). */
export function stageCounts(nodes: GraphArtifact[]): Record<string, number> {
  const order = ['PROBLEM', 'EVIDENCE', 'FINDING', 'PREDICTION', 'PRESCRIPTION', 'ALTERNATIVE', 'DECISION', 'ACTION', 'EXECUTION', 'RESULT', 'FROZEN'];
  const out: Record<string, number> = {};
  for (const k of order) out[k] = 0;
  for (const n of nodes) out[n.kind] = (out[n.kind] ?? 0) + 1;
  return out;
}

/** Node ids of a given kind (real). */
export function kindNodeIds(nodes: GraphArtifact[], kind: string): string[] {
  return nodes.filter((n) => n.kind === kind).map((n) => n.id);
}
