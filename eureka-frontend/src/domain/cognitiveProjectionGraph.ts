import type {
  CognitiveProjectionDTO,
  Authority,
  HumanDecisionDTO,
} from './cognitiveProjection';

/**
 * LS3 §9/§11 — Knowledge Map + Provenance/Lineage graph model.
 *
 * Converts the SINGLE CognitiveProjectionDTO into a governed graph:
 *  - `nodes`: EVERY real artifact the backend emitted (finding / prediction /
 *    alternative / decision / action / execution / result / frozen), each carrying its
 *    id, kind, label, status, authority, provenance (and, where the state exposes it,
 *    evidence + uncertainty + producing EM + the canonical source field).
 *  - `edges`: connections using ONLY real semantics:
 *        derived_from | supports | produced_by | selected_by | authorized_by |
 *        executed_as | frozen_as
 *    The word "causes" is never used.
 *
 * Anti-hallucination rules (mirror LS86):
 *  - A node exists ONLY if the DTO has a real artifact for it. Missing links render as
 *    "DATA NOT AVAILABLE" in the UI — never fabricated.
 *  - The human decision is read ONLY from the DTO `humanDecision` (never
 *    `recommendedOption`). The recommended option is surfaced as a distinct status on
 *    its alternative node, never conflated with the human selection.
 *  - `projectionConflict` (ActionPlan ≠ human decision) is represented by TWO distinct
 *    `selected_by` edges to two different alternatives — it is never auto-corrected.
 */

export type NodeKind =
  | 'PROBLEM'
  | 'EVIDENCE'
  | 'FINDING'
  | 'PREDICTION'
  | 'PRESCRIPTION'
  | 'ALTERNATIVE'
  | 'DECISION'
  | 'ACTION'
  | 'EXECUTION'
  | 'RESULT'
  | 'FROZEN';

export type EdgeSemantic =
  | 'derived_from'
  | 'supports'
  | 'produced_by'
  | 'selected_by'
  | 'authorized_by'
  | 'executed_as'
  | 'frozen_as';

export const ALLOWED_EDGE_SEMANTICS: EdgeSemantic[] = [
  'derived_from',
  'supports',
  'produced_by',
  'selected_by',
  'authorized_by',
  'executed_as',
  'frozen_as',
];

export interface GraphArtifact {
  id: string;                       // node id (real artifact id or stable synthetic)
  kind: NodeKind;
  /** Real backend artifact id (or null when the store did not emit one). */
  artifactId: string | null;
  label: string;
  status: string;
  authority: Authority;
  provenance: string[];
  evidence: string[];
  uncertainty: string;
  /** Producing 8-EM (role label, e.g. 'EM Predictor'). */
  em: string;
  /** Canonical field this datum projects (connectivity, §30). */
  sourceField: string;
  /** True when this alternative is the system's recommendation (recommended_option). */
  recommended: boolean;
  /** True when this alternative is the human's selection (human_decision). */
  humanSelected: boolean;
  /** Short human description (alternative description / finding statement / etc). */
  description: string;
  /** Real numeric value for a prediction (ACFL/GCLV deterministic), or null for
   *  NOT_EVALUATED / DATA NOT AVAILABLE. NEVER synthesized (single source). */
  numericValue?: number | null;
  /** Prediction model type + evidence refs (used for the honest MATHEMATICAL FIELD). */
  modelType?: string;
  /** Real action_plan step count (drives the ACTION discrete-segment glyph). */
  stepCount?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: EdgeSemantic;
}

export interface CognitiveProjectionGraph {
  nodes: GraphArtifact[];
  edges: GraphEdge[];
  /** Real EVI→FND→PRED→PRESC→DEC→ACT→EXEC→FROZEN ids from the DTO lineage (existing only). */
  lineage: string[];
}

const str = (v: unknown): string => (typeof v === 'string' ? v : v == null ? '' : String(v));

/** Map a node to the EM that produced it (role label used in the rail & inspector). */
function emFor(kind: NodeKind): string {
  switch (kind) {
    case 'PROBLEM':
      return 'EM Core';
    case 'EVIDENCE':
      return 'EM Structurer';
    case 'FINDING':
      return 'EM Descriptor';
    case 'PREDICTION':
      return 'EM Predictor';
    case 'PRESCRIPTION':
    case 'ALTERNATIVE':
    case 'DECISION':
      return 'EM Prescriptor';
    case 'ACTION':
    case 'EXECUTION':
    case 'FROZEN':
      return 'EM Installer';
    case 'RESULT':
      return 'EM Publisher';
    default:
      return 'EM Core';
  }
}

/** Canonical source field for connectivity (§30). */
function sourceFieldFor(kind: NodeKind, fallbackRef: string): string {
  switch (kind) {
    case 'PROBLEM':
      return 'problem';
    case 'EVIDENCE':
      return 'extracted_evidence.' + fallbackRef;
    case 'FINDING':
      return 'knowledge.findings[]';
    case 'PREDICTION':
      return 'predictive_knowledge.predictions[]';
    case 'ALTERNATIVE':
      return 'prescriptive_knowledge.prescriptions[].alternatives[]';
    case 'PRESCRIPTION':
      return 'prescriptive_knowledge.prescriptions[]';
    case 'DECISION':
      return 'human_decision';
    case 'ACTION':
      return 'action_plan';
    case 'EXECUTION':
      return 'execution_state';
    case 'RESULT':
      return 'state.result';
    case 'FROZEN':
      return 'frozen_result';
    default:
      return 'DATA_SOURCE_NOT_IDENTIFIED';
  }
}

/** Build the governed graph from the single projection. Pure & side-effect free. */
export function buildCognitiveProjectionGraph(p: CognitiveProjectionDTO): CognitiveProjectionGraph {
  const nodes: GraphArtifact[] = [];
  const edges: GraphEdge[] = [];

  // id -> nodeId lookup for edge resolution (evidenceRefs may reference evidence/finding ids).
  const byRef = new Map<string, string>();

  const addNode = (n: GraphArtifact) => {
    nodes.push(n);
    // Register under the real artifact id AND under the node id so edges resolve.
    if (n.artifactId) byRef.set(n.artifactId, n.id);
    byRef.set(n.id, n.id);
    // Also register under short refs (e.g. 'ALT-01')
  };

  const addEdge = (from: string, to: string, label: EdgeSemantic) => {
    const source = resolveRef(from);
    const target = resolveRef(to);
    if (!source || !target || source === target) return;
    if (!ALLOWED_EDGE_SEMANTICS.includes(label)) return;
    edges.push({ id: `${source}|${label}|${target}`, source, target, label });
  };

  const resolveRef = (ref: string): string | null => byRef.get(ref) ?? null;

  const recommended = str(p.recommendedOption);
  const humanSelected = str(p.humanDecision.selectedAlternativeId);

  // ---- PROBLEM ----
  if (p.problem && (p.question || p.problem.id)) {
    addNode({
      id: p.problem.id || 'PROBLEM',
      kind: 'PROBLEM',
      artifactId: p.problem.id,
      label: 'Problem / Question',
      status: p.problem.authority === 'PYTHON_GOVERNED' ? 'GOVERNED' : 'LLM_CANDIDATE',
      authority: p.problem.authority,
      provenance: ['EM Core → problem.objective', 'Intake → work.userIntent'],
      evidence: [],
      uncertainty: 'Not quantified.',
      em: 'EM Core',
      sourceField: 'problem',
      recommended: false,
      humanSelected: false,
      description: p.question,
    });
  }

  // ---- EVIDENCE ----
  p.evidence.forEach((e) => {
    const authority: Authority = e.grounded ? 'VALIDATED' : 'UNSUPPORTED';
    addNode({
      id: e.id,
      kind: 'EVIDENCE',
      artifactId: e.id,
      label: `Evidence ${e.id}`,
      status: e.grounded ? 'grounded' : 'UNSUPPORTED',
      authority,
      provenance: [],
      evidence: [],
      uncertainty: e.grounded ? `Grounded on ${e.sourceText.length} chars.` : 'No text block extracted.',
      em: 'EM Structurer',
      sourceField: sourceFieldFor('EVIDENCE', e.id),
      recommended: false,
      humanSelected: false,
      description: e.sourceText.slice(0, 90),
    });
  });

  // ---- FINDINGS ----
  p.findings.forEach((f) => {
    addNode({
      id: f.id,
      kind: 'FINDING',
      artifactId: f.id,
      label: `Finding ${f.id}`,
      status: f.status,
      authority: f.authority,
      provenance: f.provenance,
      evidence: f.evidenceRefs,
      uncertainty: f.status === 'UNSUPPORTED' ? 'Not supported by evidence.' : 'Not quantified.',
      em: 'EM Descriptor',
      sourceField: sourceFieldFor('FINDING', f.id),
      recommended: false,
      humanSelected: false,
      description: f.statement,
    });
    // finding -> evidence (derived_from)
    f.evidenceRefs.forEach((ref) => addEdge(f.id, ref, 'derived_from'));
  });

  // ---- PREDICTIONS ----
  p.predictions.forEach((pr) => {
    const notEvaluated = pr.value == null || /NOT_EVALUATED/i.test(pr.status);
    addNode({
      id: pr.id,
      kind: 'PREDICTION',
      artifactId: pr.id,
      label: `Prediction ${pr.id}`,
      status: pr.status,
      authority: pr.authority,
      provenance: pr.provenance,
      evidence: pr.evidenceRefs,
      uncertainty: notEvaluated
        ? 'NOT EVALUATED — no numeric value was produced.'
        : `Predicted value: ${pr.value}.`,
      em: 'EM Predictor',
      sourceField: sourceFieldFor('PREDICTION', pr.id),
      recommended: false,
      humanSelected: false,
      description: `${pr.modelType} · ${pr.status}`,
      numericValue: pr.value,
      modelType: pr.modelType,
    });
    // prediction -> finding (derived_from); fall back to evidence when refs are evidence ids.
    pr.evidenceRefs.forEach((ref) => addEdge(pr.id, ref, 'derived_from'));
  });

  // ---- PRESCRIPTION + ALTERNATIVES ----
  if (p.prescription) {
    addNode({
      id: p.prescription.id || 'PRESC',
      kind: 'PRESCRIPTION',
      artifactId: p.prescription.id,
      label: `Prescription ${p.prescription.id || ''}`,
      status: 'SELECTED',
      authority: p.prescription.authority,
      provenance: [],
      evidence: [],
      uncertainty: 'Not quantified.',
      em: 'EM Prescriptor',
      sourceField: sourceFieldFor('PRESCRIPTION', p.prescription.id || 'PRESC'),
      recommended: false,
      humanSelected: false,
      description: p.prescription.rationale.slice(0, 90),
    });
    const prescId = p.prescription.id || 'PRESC';
    const prescAuthority = p.prescription.authority;
    const prescRationale = p.prescription.rationale;
    p.prescription.alternatives.forEach((a) => {
      const isRec = a.id === recommended || a.id === p.recommendedOption;
      const isHum = a.id === humanSelected;
      addNode({
        id: a.id,
        kind: 'ALTERNATIVE',
        artifactId: a.id,
        label: `Alternative ${a.id}`,
        status: isHum ? 'HUMAN_SELECTED' : isRec ? 'RECOMMENDED' : 'CANDIDATE',
        authority: prescAuthority,
        provenance: [],
        evidence: [],
        uncertainty: 'Not quantified.',
        em: 'EM Prescriptor',
        sourceField: sourceFieldFor('ALTERNATIVE', a.id),
        recommended: isRec,
        humanSelected: isHum,
        description: a.description,
      });
      addEdge(a.id, prescId, 'produced_by');
    });
    if (p.prescription.id) byRef.set(p.prescription.id, p.prescription.id);
  }

  // ---- DECISION (only from human_decision) ----
  const hd: HumanDecisionDTO = p.humanDecision;
  const decNodeId = hd.decisionId
    ? hd.decisionId
    : hd.selectedAlternativeId
      ? `DECISION:${hd.selectedAlternativeId}`
      : null;
  if (decNodeId) {
    addNode({
      id: decNodeId,
      kind: 'DECISION',
      artifactId: hd.decisionId,
      label: hd.decisionId ? `Human decision ${hd.decisionId}` : 'Human decision',
      status: str(hd.status) || 'HUMAN_AUTHORIZED',
      authority: 'HUMAN_AUTHORIZED',
      provenance: hd.preserved ? ['human_decision → selected_alternative_id'] : [],
      evidence: [],
      uncertainty: hd.selectedAlternativeId
        ? `Human selected ${hd.selectedAlternativeId}.`
        : 'Pending human selection.',
      em: 'EM Prescriptor / EM Installer',
      sourceField: 'human_decision',
      recommended: false,
      humanSelected: true,
      description: hd.selectedAlternativeId
        ? `Human decision selected alternative ${hd.selectedAlternativeId}.`
        : 'DECISION PENDING.',
    });
  }

  // ---- ACTION PLAN ----
  if (p.actionPlan) {
    addNode({
      id: p.actionPlan.id || 'ACTION',
      kind: 'ACTION',
      artifactId: p.actionPlan.id,
      label: `Action plan ${p.actionPlan.id || ''}`,
      status: p.actionPlan.status,
      authority: p.actionPlan.authority,
      provenance: [],
      evidence: [],
      uncertainty: 'Not quantified.',
      em: 'EM Actioner',
      sourceField: sourceFieldFor('ACTION', p.actionPlan.id || 'AP'),
      recommended: false,
      humanSelected: false,
      description: `Action plan selecting ${p.actionPlan.selectedAlternativeId || 'n/a'}.`,
      stepCount: Array.isArray(p.actionPlan.steps) ? p.actionPlan.steps.length : 0,
    });
    if (p.actionPlan.id) byRef.set(p.actionPlan.id, p.actionPlan.id);
  }

  // ---- EXECUTION (SIMULATED preserved) ----
  if (p.execution) {
    addNode({
      id: p.execution.id || 'EXECUTION',
      kind: 'EXECUTION',
      artifactId: p.execution.id,
      label: `Execution ${p.execution.id || ''}`,
      status: p.execution.status,
      authority: 'SIMULATED',
      provenance: [],
      evidence: [],
      uncertainty: p.execution.simulated ? 'SIMULATED — not externally executed.' : 'Not quantified.',
      em: 'EM Installer',
      sourceField: sourceFieldFor('EXECUTION', p.execution.id || 'EXEC'),
      recommended: false,
      humanSelected: false,
      description: `${p.execution.status} · level ${p.execution.level || 'n/a'} · simulated`,
    });
    if (p.execution.id) byRef.set(p.execution.id, p.execution.id);
  }

  // ---- RESULT ----
  if (p.result) {
    addNode({
      id: p.result.id || 'RESULT',
      kind: 'RESULT',
      artifactId: p.result.id,
      label: `Result ${p.result.id || ''}`,
      status: p.result.status,
      authority: 'PUBLISHED',
      provenance: [],
      evidence: [],
      uncertainty: 'Not quantified.',
      em: 'EM Publisher',
      sourceField: sourceFieldFor('RESULT', p.result.id || 'WR'),
      recommended: false,
      humanSelected: false,
      description: p.result.summary,
    });
    if (p.result.id) byRef.set(p.result.id, p.result.id);
  }

  // ---- FROZEN RESULT ----
  if (p.frozenResult) {
    addNode({
      id: p.frozenResult.id || 'FROZEN',
      kind: 'FROZEN',
      artifactId: p.frozenResult.id,
      label: `Frozen result ${p.frozenResult.id || ''}`,
      status: p.frozenResult.status,
      authority: 'FROZEN',
      provenance: p.frozenResult.signature ? [`freeze_signature=${p.frozenResult.signature}`] : [],
      evidence: [],
      uncertainty: p.frozenResult.signature ? `Frozen (signature ${p.frozenResult.signature}).` : 'Frozen.',
      em: 'EM Installer',
      sourceField: sourceFieldFor('FROZEN', p.frozenResult.id || 'FROZEN'),
      recommended: false,
      humanSelected: false,
      description: 'Frozen result.',
    });
    if (p.frozenResult.id) byRef.set(p.frozenResult.id, p.frozenResult.id);
  }

  // ---- EDGES (real semantics; never causation) ----
  // decision -> selected alternative (selected_by)
  if (decNodeId && humanSelected) addEdge(humanSelected, decNodeId, 'selected_by');
  // prescription -> decision (supports)
  if (p.prescription && decNodeId) addEdge(p.prescription.id || 'PRESC', decNodeId, 'supports');
  // action plan -> decision (authorized_by)
  if (p.actionPlan && decNodeId) addEdge(p.actionPlan.id || 'ACTION', decNodeId, 'authorized_by');
  // action plan -> its selected alternative (selected_by) — surfaces conflicts, never corrects
  if (p.actionPlan?.selectedAlternativeId) {
    addEdge(p.actionPlan.selectedAlternativeId, p.actionPlan.id || 'ACTION', 'selected_by');
  }
  // execution -> action plan (executed_as)
  if (p.execution && p.actionPlan) addEdge(p.execution.id || 'EXECUTION', p.actionPlan.id || 'ACTION', 'executed_as');
  // execution -> result (supports)
  if (p.execution && p.result) addEdge(p.execution.id || 'EXECUTION', p.result.id || 'RESULT', 'supports');
  // frozen -> result (frozen_as)
  if (p.frozenResult && p.result) addEdge(p.frozenResult.id || 'FROZEN', p.result.id || 'RESULT', 'frozen_as');

  return { nodes, edges, lineage: p.lineage };
}

/** The 8-EM related artifact node-ids (for the EM rail click affordance). */
export function relatedArtifactsForEM(
  em: string,
  g: CognitiveProjectionGraph,
): GraphArtifact[] {
  const key = em.toLowerCase();
  if (key.includes('predictor')) {
    return g.nodes.filter((n) => ['PREDICTION', 'FINDING', 'EVIDENCE'].includes(n.kind));
  }
  if (key.includes('prescriptor')) {
    return g.nodes.filter((n) => ['ALTERNATIVE', 'DECISION', 'PRESCRIPTION'].includes(n.kind));
  }
  if (key.includes('installer')) {
    return g.nodes.filter((n) => ['ACTION', 'EXECUTION', 'FROZEN'].includes(n.kind));
  }
  if (key.includes('descriptor')) {
    return g.nodes.filter((n) => ['FINDING'].includes(n.kind));
  }
  if (key.includes('structurer')) {
    return g.nodes.filter((n) => ['EVIDENCE'].includes(n.kind));
  }
  if (key.includes('publisher')) {
    return g.nodes.filter((n) => ['RESULT'].includes(n.kind));
  }
  // Map the known rail labels to their producing EM role.
  if (key.includes('core')) return g.nodes.filter((n) => ['PROBLEM'].includes(n.kind));
  return g.nodes;
}

/** Human-readable role line for an EM (status/role, §5). */
export function emRoleLabel(em: string): string {
  const key = em.toLowerCase();
  if (key.includes('predictor')) return 'ACFL_DETERMINISTIC · MathEngine · GCLV';
  if (key.includes('prescriptor')) return 'Alternatives → HITL decision';
  if (key.includes('installer')) return 'ActionPlan → Execution → FrozenResult';
  if (key.includes('descriptor')) return 'Findings from evidence';
  if (key.includes('structurer')) return 'Evidence ingestion + extraction';
  if (key.includes('publisher')) return 'Result publication';
  if (key.includes('actioner')) return 'Action plan synthesis';
  if (key.includes('core')) return 'Question enrichment';
  return 'EM role';
}
