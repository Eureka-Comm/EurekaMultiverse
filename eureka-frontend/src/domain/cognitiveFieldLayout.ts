import type {
  CognitiveProjectionGraph,
  GraphArtifact,
  NodeKind,
} from './cognitiveProjectionGraph';

/**
 * LS91 -> LS93 v5 — COGNITIVE FIELD LAYOUT (pure, deterministic, single-source).
 *
 * This module is the ONLY place that decides where a cognitive artifact lives in
 * the spatial field. It reads exclusively from the governed graph
 * (`CognitiveProjectionGraph`, itself built from the SINGLE `CognitiveProjectionDTO`).
 * It NEVER invents an artifact, a numeric value, a relation, a stage, or a weight
 * the graph does not contain.
 *
 * LS93 spatial semantics (each maps a REAL attribute, not decoration):
 *   · X-axis  → the COGNITIVE AXIS / PATH: the authority & decision progression
 *               QUESTION → DISCOVERY → EVALUATION → DECISION → ACTION → EXECUTION →
 *               RESULT. One dominant composition. Left-to-right walkthrough.
 *   · Z-axis  → DISPERSION within a stage + the FIELD: secondary context (evidence,
 *               prescription alternatives) disperses around the path node it
 *               converges INTO; never a floating object without an edge to its parent.
 *   · Y-axis  → AUTHORITY / VALIDITY HEIGHT (validated & human-authority float
 *               higher; unsupported / not-evaluated / frozen sink lower). Deterministic.
 *   · RADIUS  → REAL SEMANTIC WEIGHT (evidence count, finding confidence/validation,
 *               alternative count, decision authority, result terminality). The
 *               result & human decision are always the largest; evidence the smallest.
 *
 * Layers (so it is never a flat graph again):
 *   · LAYER 1 = cognitive structure (question / action / decision / result / frozen)
 *   · LAYER 2 = semantic artifacts (evidence / finding / prediction / prescription /
 *               alternative) — medium, by selection
 *   · LAYER 3 = relationships (edges) — low, subtle, always present
 *   · LAYER 4 = context / inspection (labels, inspector, legend) — on demand
 *
 * The layout is a pure function of the graph, so it is fully unit-testable and
 * identical across renders for identical governed state.
 */

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

/** Spatial grammar for a cognitive class (NOT boxes + edges). */
export type FieldGeometry =
  | 'question'    // QUESTION (ring) — larger than evidence; the inquiry origin
  | 'evidence'    // EVIDENCE — small sphere / cluster converging into a finding
  | 'finding'     // FINDING — concentrated sphere, ∝ confidence/weight
  | 'prediction'  // PREDICTION (plane / ghost wireframe when NOT_EVALUATED)
  | 'prescription' // PRESCRIPTION (branch fan from a common point ∝ alternative count)
  | 'alternative' // ALTERNATIVE — candidate point in the prescription region
  | 'decision'    // DECISION — double-ring authority node (largest in the prescription region)
  | 'action'      // ACTION — discrete segments (count = real step count)
  | 'execution'   // EXECUTION — segment with real visual state (pending/running/simulated/completed)
  | 'result'      // RESULT — terminal node (largest, end of path; stabilized)
  | 'frozen'      // FROZEN — sealed / stabilized terminal state
  | 'unknown';

/** Derived, honest tone used for color + elevation (mapped from REAL status). */
export type Tone =
  | 'VALIDATED'
  | 'HUMAN'
  | 'PUBLISHED'
  | 'RECOMMENDED'
  | 'CANDIDATE'
  | 'PENDING'
  | 'UNSUPPORTED'
  | 'NOT_EVALUATED'
  | 'SIMULATED'
  | 'FROZEN'
  | 'NEUTRAL';

/** Which visual layer the artifact belongs to (L1 structure, L2 artifact). */
export type FieldLayer = 1 | 2;

export interface FieldEntity {
  id: string;
  artifactId: string | null;
  kind: NodeKind;
  label: string;
  description: string;
  status: string;
  authority: string;
  em: string;
  evidence: string[];
  provenance: string[];
  sourceField: string;
  recommended: boolean;
  humanSelected: boolean;
  numericValue: number | null;
  modelType?: string;
  geometry: FieldGeometry;
  position: Vec3;
  radius: number;
  stageIndex: number;
  stageId: string;
  tone: Tone;
  /** 1 = cognitive structure (L1, max), 2 = semantic artifact (L2, medium). */
  layer: FieldLayer;
  /** Real weight that drove the radius (for the inspector / honest HUD). */
  weight: number;
}

/** A stage of the primary cognitive axis as a spatial anchor. */
export interface FieldStage {
  id: string;
  index: number;
  anchor: Vec3;
  kind: NodeKind; // representative kind shown in stage label
  hasArtifacts: boolean;
}

/** A real relation placed in the field (thin, secondary to the thread). */
export interface FieldLink {
  id: string;
  source: string;
  target: string;
  label: string; // real semantic (derived_from | supports | produced_by | ...)
  kind: 'provenance' | 'selection';
}

/** An empty cognitive stage collapsed to an inline gap marker (no fake node). */
export interface FieldGap {
  id: string;
  index: number;
  anchor: Vec3;
  kind: NodeKind;
  /** Why it is empty (real, e.g. the honest "not reached / data not available"). */
  note: string;
}

export interface CognitiveFieldLayout {
  entities: FieldEntity[];
  /** The dominant cognitive axis spline points, in cognitive order (x, y=0, z=0). */
  thread: Vec3[];
  stages: FieldStage[];
  links: FieldLink[];
  /** Stages absent from the state, collapsed to subtle inline gap markers. */
  gaps: FieldGap[];
  /** Derived focus mask: node id -> salience (1.0 focal … 0.14 attenuated). */
  salience: Map<string, number>;
  /** Whether provenance edge labels are currently revealed. */
  provenanceVisible: boolean;
  /** The focused entity id, if any. */
  focusedId: string | null;
  /** Initial semantic-camera focus: RESULT if it exists, else the highest-authority
   *  pending artifact. Never a free orbital view. */
  cameraStartId: string | null;
  /** True when a decision has NOT been reached (honest OPEN state). */
  isOpen: boolean;
}

// ---- cognitive-stage ordering (the dominant trajectory) ----------------------

const STAGE_ORDER: { id: string; kind: NodeKind }[] = [
  { id: 'QUESTION', kind: 'PROBLEM' },
  { id: 'EVIDENCE', kind: 'EVIDENCE' },
  { id: 'FINDING', kind: 'FINDING' },
  { id: 'PREDICTION', kind: 'PREDICTION' },
  { id: 'PRESC', kind: 'PRESCRIPTION' },
  { id: 'DECISION', kind: 'DECISION' },
  { id: 'ACTION', kind: 'ACTION' },
  { id: 'EXECUTION', kind: 'EXECUTION' },
  { id: 'RESULT', kind: 'RESULT' },
  { id: 'FROZEN', kind: 'FROZEN' },
];

const KIND_TO_STAGE: Record<NodeKind, string> = {
  PROBLEM: 'QUESTION',
  EVIDENCE: 'EVIDENCE',
  FINDING: 'FINDING',
  PREDICTION: 'PREDICTION',
  PRESCRIPTION: 'PRESC',
  ALTERNATIVE: 'PRESC',
  DECISION: 'DECISION',
  ACTION: 'ACTION',
  EXECUTION: 'EXECUTION',
  RESULT: 'RESULT',
  FROZEN: 'FROZEN',
};

// Stage anchors along X (progression). Abstract world units; the renderer scales
// the camera to fit. Ordered: origin -> terminal, so the walkthrough reads left->right.
// Deliberately COMPACT so the whole cognitive axis + its field are legible together.
const STAGE_X: Record<string, number> = {
  QUESTION: 0,
  EVIDENCE: 92,
  FINDING: 184,
  PREDICTION: 286,
  PRESC: 388,
  DECISION: 480,
  ACTION: 582,
  EXECUTION: 672,
  RESULT: 774,
  FROZEN: 866,
};

const GEOMETRY_BY_KIND: Record<NodeKind, FieldGeometry> = {
  PROBLEM: 'question',
  EVIDENCE: 'evidence',
  FINDING: 'finding',
  PREDICTION: 'prediction',
  PRESCRIPTION: 'prescription',
  ALTERNATIVE: 'alternative',
  DECISION: 'decision',
  ACTION: 'action',
  EXECUTION: 'execution',
  RESULT: 'result',
  FROZEN: 'frozen',
};

/** L1 = cognitive structure (path/authority), L2 = semantic artifact (field). */
const LAYER_BY_KIND: Record<NodeKind, FieldLayer> = {
  PROBLEM: 1,
  EVIDENCE: 2,
  FINDING: 2,
  PREDICTION: 2,
  PRESCRIPTION: 2,
  ALTERNATIVE: 2,
  DECISION: 1,
  ACTION: 1,
  EXECUTION: 1,
  RESULT: 1,
  FROZEN: 1,
};

// ---- tone mapping (REAL status/authority -> spatial height + color) ---------

function toneOf(a: GraphArtifact): Tone {
  if (a.kind === 'DECISION' || a.authority === 'HUMAN_AUTHORIZED') return 'HUMAN';
  if (a.authority === 'VALIDATED' || a.authority === 'PYTHON_GOVERNED') return 'VALIDATED';
  if (a.authority === 'PUBLISHED' || a.kind === 'RESULT') return 'PUBLISHED';
  if (a.authority === 'FROZEN' || a.kind === 'FROZEN') return 'FROZEN';
  if (a.authority === 'SIMULATED') return 'SIMULATED';
  if (a.authority === 'NOT_EVALUATED' || /NOT_EVALUATED/i.test(a.status)) return 'NOT_EVALUATED';
  if (a.authority === 'UNSUPPORTED' || a.status === 'UNSUPPORTED') return 'UNSUPPORTED';
  if (a.authority === 'PENDING' || /pending/i.test(a.status)) return 'PENDING';
  if (a.humanSelected) return 'HUMAN';
  if (a.recommended) return 'RECOMMENDED';
  return 'NEUTRAL';
}

/** Real status/authority -> elevation (a spatial height cue, not a score). */
const TONE_ELEVATION: Record<Tone, number> = {
  HUMAN: 26,
  VALIDATED: 18,
  PUBLISHED: 22,
  RECOMMENDED: 14,
  CANDIDATE: 8,
  NEUTRAL: 6,
  PENDING: 3,
  UNSUPPORTED: -6,
  NOT_EVALUATED: -10,
  SIMULATED: 0,
  FROZEN: -14,
};

// ---- deterministic hash (stable across calls) ------------------------------

function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function jitter(seed: string, span: number): number {
  const h = hash(seed);
  return ((h % 2000) / 1000 - 1) * span;
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

// ---- REAL semantic weight -> radius (size hierarchy) ------------------------
// Radius ∝ a real attribute. Provenance-friendly fallback keeps every artifact
// legible while preserving the hierarchy: result > decision > question > finding >
// prediction > prescription/alternative > evidence.

function weightOf(a: GraphArtifact, graph: CognitiveProjectionGraph): number {
  switch (a.kind) {
    case 'PROBLEM':
      return 1.0;
    case 'EVIDENCE': {
      // A grounded evidence item carries more weight than an extraction that
      // produced no text block.
      return a.authority === 'VALIDATED' ? 1.25 : 0.75;
    }
    case 'FINDING': {
      const nRefs = Math.min(4, a.evidence?.length ?? 0);
      const base = a.authority === 'VALIDATED' || a.authority === 'PYTHON_GOVERNED' ? 1.35 : 0.9;
      return base * (1 + 0.06 * nRefs);
    }
    case 'PREDICTION':
      return 1.0;
    case 'PRESCRIPTION': {
      const alts = countProducedBy(graph, a.id);
      return 1.0 + 0.18 * Math.min(5, alts);
    }
    case 'ALTERNATIVE':
      return a.humanSelected ? 1.35 : a.recommended ? 1.2 : 1.0;
    case 'DECISION':
      return 1.0;
    case 'ACTION': {
      const steps = (a as { stepCount?: number }).stepCount ?? 0;
      return 1.0 + 0.08 * Math.min(8, steps);
    }
    case 'EXECUTION':
      return 1.0;
    case 'RESULT':
      return 1.0;
    case 'FROZEN':
      return 1.0;
    default:
      return 1.0;
  }
}

/** Count how many graph edges carry `produced_by` INTO a node (real alternative count). */
function countProducedBy(graph: CognitiveProjectionGraph, id: string): number {
  let n = 0;
  graph.edges.forEach((e) => { if (e.target === id && e.label === 'produced_by') n += 1; });
  return n;
}

const BASE_RADIUS: Record<NodeKind, number> = {
  PROBLEM: 16,
  EVIDENCE: 6,
  FINDING: 12,
  PREDICTION: 12,
  PRESCRIPTION: 13,
  ALTERNATIVE: 9,
  DECISION: 19,
  ACTION: 13,
  EXECUTION: 11,
  RESULT: 22,
  FROZEN: 15,
};

function radiusFor(a: GraphArtifact, graph: CognitiveProjectionGraph): number {
  const w = weightOf(a, graph);
  // Human decision & result are always dominant (authority + terminality), and
  // clearly larger than any prescription/alternative (never confusable).
  if (a.kind === 'DECISION') return BASE_RADIUS.DECISION * w;
  if (a.kind === 'RESULT') return BASE_RADIUS.RESULT;
  if (a.kind === 'FROZEN') return BASE_RADIUS.FROZEN;
  if (a.kind === 'PROBLEM') return BASE_RADIUS.PROBLEM;
  return BASE_RADIUS[a.kind] * w;
}

// ---- focus mask -------------------------------------------------------------

/** Distance-1 neighbourhood (undirected) of the focused node. */
function neighboursOf(graph: CognitiveProjectionGraph, id: string): Set<string> {
  const out = new Set<string>();
  graph.edges.forEach((e) => {
    if (e.source === id) out.add(e.target);
    if (e.target === id) out.add(e.source);
  });
  return out;
}

/**
 * Compute the focus mask. When no node is focused, every entity is equally
 * salient (1.0), i.e. the whole field is legible. When a node is focused:
 *   focal=1.0 · direct neighbours=0.85 · 2nd hop=0.55 · unrelated=0.14.
 */
export function computeFocusMask(
  graph: CognitiveProjectionGraph,
  focusedId: string | null,
): Map<string, number> {
  const mask = new Map<string, number>();
  graph.nodes.forEach((n) => mask.set(n.id, 1));
  if (!focusedId || !graph.nodes.some((n) => n.id === focusedId)) return mask;

  const first = neighboursOf(graph, focusedId);
  const second = new Set<string>();
  first.forEach((nid) => neighboursOf(graph, nid).forEach((n) => second.add(n)));

  for (const id of mask.keys()) {
    if (id === focusedId) mask.set(id, 1.0);
    else if (first.has(id)) mask.set(id, 0.85);
    else if (second.has(id)) mask.set(id, 0.55);
    else mask.set(id, 0.14);
  }
  return mask;
}

// ---- the layout -------------------------------------------------------------

/** Compute the semantic-camera start: RESULT if present, else the highest-authority
 *  pending / open artifact. Never a free orbital view. */
function computeCameraStart(entities: FieldEntity[]): string | null {
  const result = entities.find((e) => e.kind === 'RESULT');
  if (result) return result.id;
  // highest-authority pending artifact (decision selection or the most elevated one)
  const openable = entities
    .filter((e) => e.tone !== 'FROZEN')
    .sort((a, b) => TONE_ELEVATION[b.tone] - TONE_ELEVATION[a.tone]);
  return openable[0]?.id ?? entities[0]?.id ?? null;
}

export function layoutCognitiveField(
  graph: CognitiveProjectionGraph,
  options: { focusedId?: string | null; provenanceVisible?: boolean; chapterKinds?: string[] | null } = {},
): CognitiveFieldLayout {
  const focusedId = options.focusedId ?? null;
  const provenanceVisible = options.provenanceVisible ?? false;
  const chapterKinds = options.chapterKinds?.length ? new Set(options.chapterKinds) : null;

  const byStage = new Map<string, GraphArtifact[]>();
  graph.nodes.forEach((n) => {
    const sid = KIND_TO_STAGE[n.kind] ?? 'FINDING';
    if (!byStage.has(sid)) byStage.set(sid, []);
    byStage.get(sid)!.push(n);
  });

  const entities: FieldEntity[] = graph.nodes.map((a) => {
    const stageId = KIND_TO_STAGE[a.kind] ?? 'FINDING';
    const stageIndex = STAGE_ORDER.findIndex((s) => s.id === stageId);
    const group = byStage.get(stageId) ?? [];
    const idx = group.findIndex((x) => x.id === a.id);
    const n = group.length;
    const baseX = STAGE_X[stageId] ?? 200;
    const tone = toneOf(a);
    const elevation = TONE_ELEVATION[tone];

    // Dispersion within the stage. For content artifacts (finding / prediction) we
    // fan them horizontally (x) so a multi-item cluster reads as a constellation,
    // not a depth-stacked blob. For FIELD artifacts (EVIDENCE / ALTERNATIVE /
    // PRESCRIPTION) we push them OFF the axis (z) so they converge into the path
    // node they feed; the axis stays a clean left-to-right line.
    const isField = a.kind === 'EVIDENCE' || a.kind === 'ALTERNATIVE' || a.kind === 'PRESCRIPTION';
    const xSpread = isField ? 6 : 30;
    const zSpacing = isField ? 50 : 20;
    const xDispersion = (idx - (n - 1) / 2) * xSpread;
    const zDispersion = (idx - (n - 1) / 2) * zSpacing;
    // Field nodes also lag slightly behind their stage along X to read as a
    // tributary sweeping into the path node (never ahead of the walkthrough).
    const fieldLag = isField ? 20 : 0;
    const jx = isField ? 12 : 16;
    const x = baseX + fieldLag + xDispersion + jitter(a.id, jx);
    const z = clamp(zDispersion + jitter(a.id + '·z', isField ? 9 : 6), isField ? -118 : -80, isField ? 118 : 80);
    const position: Vec3 = { x, y: elevation + jitter(a.id + '·y', 2.4), z };

    const radius = radiusFor(a, graph);
    return {
      id: a.id,
      artifactId: a.artifactId,
      kind: a.kind,
      label: a.label,
      description: a.description,
      status: a.status,
      authority: a.authority,
      em: a.em,
      evidence: a.evidence,
      provenance: a.provenance,
      sourceField: a.sourceField,
      recommended: a.recommended,
      humanSelected: a.humanSelected,
      numericValue: a.numericValue ?? null,
      modelType: a.modelType,
      geometry: GEOMETRY_BY_KIND[a.kind] ?? 'unknown',
      position,
      radius,
      stageIndex,
      stageId,
      tone,
      layer: LAYER_BY_KIND[a.kind] ?? 2,
      weight: weightOf(a, graph),
    };
  });

  const stages: FieldStage[] = STAGE_ORDER.map((s, i) => ({
    id: s.id,
    index: i,
    anchor: { x: STAGE_X[s.id] ?? i * 115, y: 0, z: 0 },
    kind: s.kind,
    hasArtifacts: (byStage.get(s.id) ?? []).length > 0,
  }));

  // Empty stages, collapsed to subtle inline gap markers (never a fake node /
  // never an empty card wall). Note is real (not reached / data not available).
  const gaps: FieldGap[] = STAGE_ORDER.filter((s) => (byStage.get(s.id) ?? []).length === 0 && s.id !== 'QUESTION')
    .map((s, i) => ({
      id: s.id,
      index: i + 1,
      anchor: { x: STAGE_X[s.id] ?? 0, y: 0, z: 0 },
      kind: s.kind,
      note: s.id === 'DECISION' ? 'decision pending' : s.id === 'ACTION' || s.id === 'EXECUTION' ? 'not reached' : 'data not available',
    }));

  // The dominant cognitive axis spline through PRESENT path stages, in order.
  const present = STAGE_ORDER.filter((s) => (byStage.get(s.id) ?? []).length > 0 && s.id !== 'EVIDENCE' && s.id !== 'PRESC');
  const thread: Vec3[] = present.map((s) => ({ x: STAGE_X[s.id] ?? 0, y: 0, z: 0 }));

  const links: FieldLink[] = graph.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    kind: e.label === 'selected_by' || e.label === 'authorized_by' ? 'selection' : 'provenance',
  }));

  const salience = computeFocusMask(graph, focusedId);
  if (chapterKinds) {
    for (const e of entities) {
      const base = salience.get(e.id) ?? 1;
      if (!chapterKinds.has(e.kind) && e.id !== focusedId) {
        salience.set(e.id, base * 0.6);
      }
    }
  }

  const cameraStartId = computeCameraStart(entities);
  const hasDecision = entities.some((e) => e.kind === 'DECISION');
  const isOpen = !hasDecision;

  return {
    entities,
    thread,
    stages,
    links,
    gaps,
    salience,
    provenanceVisible,
    focusedId,
    cameraStartId,
    isOpen,
  };
}

/** Convenience: honest label for a prediction's mathematical state. */
export function mathematicalFieldLabel(a: GraphArtifact): string {
  if (a.numericValue != null && Number.isFinite(a.numericValue)) {
    return `MATHEMATICAL FIELD · ${a.modelType || 'ACFL'} · VALUE ${Number(a.numericValue).toFixed(4)}`;
  }
  return 'MATHEMATICAL FIELD · NOT EVALUATED';
}
