import React, { useMemo } from 'react';
import type { CognitiveProjectionDTO } from '../../domain/cognitiveProjection';
import type { CognitiveProjectionGraph, GraphArtifact } from '../../domain/cognitiveProjectionGraph';
import { kindColor, statusColor } from './cognitiveColors';
import './cognitiveOperationMap.css';

/**
 * LS94 — COGNITIVE OPERATION MAP (PRIMARY comprehension surface).
 *
 * ONE screen, no scroll, no Inspector, no legend: the whole cognitive operation
 * (QUESTION → DISCOVERY → EVALUATION → DECISION → ACTION → RESULT) on a single
 * horizontal cognitive axis (origin → destination). Six *distinct* visual
 * primitives — never six cards:
 *
 *   QUESTION   = a singular OPEN ring (the origin / empty opening)
 *   DISCOVERY  = MANY source points → FEW distilled nodes (real derived_from)
 *   EVALUATION = a measurement gauge (ACFL/GCLV); NOT_EVALUATED -> empty gauge
 *   DECISION   = a sovereign vertical AUTHORITY GATE that breaks the flow
 *                (AuthorityChip visual language; RECOMMENDED ≠ HUMAN DECIDED)
 *   ACTION     = a rising N-step staircase (real actionPlan.steps)
 *   RESULT     = the DOMINANT closed terminal (AVAILABLE/FROZEN/SIMULATED/DATA NOT AVAILABLE)
 *
 * Honesty by construction: an absent stage renders an explicit NOT_EVALUATED /
 * DATA NOT AVAILABLE / DECISION PENDING marker in its own region. Never invented.
 *
 * Renders pure SVG + DOM; no window/document access at render time (SSR-safe so
 * the render-smoke suite can mount it with react-dom/server).
 */

export type OperationMapLabelPolicy = 'on' | 'off';

/** read a labels-hiding policy that still lets the forms be judged (§39). */
function readLabelPolicy(): OperationMapLabelPolicy {
  if (typeof window === 'undefined') return 'on';
  const q = new URLSearchParams(window.location.search);
  if (q.get('bare') === '1') return 'off';
  if (q.get('nolabels') === '1') return 'off';
  return 'on';
}

const W = 1240;
const H = 560;
const SPINE_Y = 452;

const COL = {
  problem: '#3b6ea8',
  evidence: '#7a6bb8',
  finding: '#4a9a63',
  prediction: '#3f8f93',
  authority: '#8250df',
  rec: '#0969da',
  action: '#3f8f93',
  result: '#55b97a',
  frozen: '#9c7f45',
  hairline: '#d0d7de',
  grid: 'rgba(0,0,0,0.05)',
  textLabel: '#656d76',
  textMicro: '#8c959f',
  textDisplay: '#1f2328',
  amber: '#b08800',
  red: '#cf222e',
};

function truncate(s: string, n: number): string {
  const t = (s || '').trim();
  return t.length > n ? t.slice(0, n - 1) + '…' : t;
}

interface DiscPoint {
  id: string;
  x: number;
  y: number;
  r: number;
}
interface DiscNode {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  status: string;
  kind: 'FINDING' | 'EVIDENCE';
}
interface DiscLink {
  fx: number;
  fy: number;
  tx: number;
  ty: number;
  grounded: boolean;
}
interface StepNode {
  order: number;
  x: number;
  y: number;
  label: string;
  status: string;
}

interface MapModel {
  question: string;
  problemAuthority: string;
  hasProblem: boolean;

  discLed: DiscPoint[];
  discNodes: DiscNode[];
  discLinks: DiscLink[];
  discEvidenceCount: number;
  discFindingCount: number;

  predCount: number;
  predAnyValue: boolean;
  predAllNotEval: boolean;
  predValues: number[];

  recOption: string | null;
  humanSelected: string | null;
  humanDecisionId: string | null;
  humanAuthority: string;
  humanPending: boolean;
  conflict: boolean;
  hasAlternatives: boolean;

  actionSteps: StepNode[];
  actionPresent: boolean;
  actionStatus: string;
  actionTotal: number;

  resultId: string | null;
  resultStatus: string;
  resultSummary: string;
  resultPresent: boolean;
  frozenId: string | null;
  frozenStatus: string;
  frozenSignature: string | null;

  executionStatus: string | null;
  executionSimulated: boolean;
}

function buildModel(dto: CognitiveProjectionDTO, graph: CognitiveProjectionGraph): MapModel {
  const problem = dto.problem;
  const question = dto.question || problem?.objective || '';

  // ---- DISCOVERY: evidence dots -> finding nodes (real derived_from) ------
  const evidence = dto.evidence || [];
  const findings = dto.findings || [];
  const D0 = 190;
  const D1 = 440;
  const E_Y = 246;
  const F_Y = 396;
  const discLed: DiscPoint[] = evidence.map((e, i) => ({
    id: e.id,
    x: evidence.length <= 1 ? (D0 + D1) / 2 : D0 + (i * (D1 - D0)) / (evidence.length - 1),
    y: E_Y,
    r: 5,
  }));
  const F_W = findings.length <= 1 ? 0 : Math.max(40, Math.min(58, (D1 - D0) / findings.length - 6));
  const discNodes: DiscNode[] = findings.map((f, i) => ({
    id: f.id,
    x: findings.length <= 1 ? (D0 + D1) / 2 : D0 + (i * (D1 - D0)) / (findings.length - 1),
    y: F_Y,
    w: F_W,
    h: 30,
    status: f.status,
    kind: 'FINDING' as const,
  }));
  const byId = new Map(discLed.map((d) => [d.id, d]));
  const discLinks: DiscLink[] = [];
  findings.forEach((f, i) => {
    (f.evidenceRefs || []).forEach((ref) => {
      const t = byId.get(ref);
      if (!t) return;
      const n = discNodes[i];
      discLinks.push({ fx: n.x + n.w / 2, fy: n.y, tx: t.x, ty: t.y + t.r, grounded: !!(dto.evidence.find((e) => e.id === ref)?.grounded) });
    });
  });

  // ---- EVALUATION: ACFL/GCLV predictions ----------------------------------
  const predictions = dto.predictions || [];
  const predValues = predictions.map((p) => p.value ?? null).filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
  const predAnyValue = predValues.length > 0;
  const predAllNotEval = predictions.length > 0 && predictions.every((p) => p.value == null || /NOT_EVALUATED/i.test(p.status));

  // ---- DECISION: human authority vs recommendation -----------------------
  const human = dto.humanDecision;
  const recOption = dto.recommendedOption || null;
  const humanSelected = human?.selectedAlternativeId || null;
  const humanPending = !humanSelected || /PENDING/i.test(human?.authority || '');

  // ---- ACTION: N real steps ---------------------------------------------
  const ap = dto.actionPlan;
  const actionSteps: StepNode[] = (ap?.steps || []).slice(0, 8).map((s, i) => ({
    order: s.order,
    x: 0,
    y: 0,
    label: truncate(s.description, 26),
    status: s.status,
  }));
  const ASX0 = 824;
  const ASX1 = 1004;
  const ASY0 = 432;
  const ASY1 = 208;
  if (actionSteps.length) {
    const n = actionSteps.length;
    actionSteps.forEach((s, i) => {
      s.x = n <= 1 ? (ASX0 + ASX1) / 2 : ASX0 + (i * (ASX1 - ASX0)) / (n - 1);
      s.y = SY1(i, n);
    });
  }
  function SY1(i: number, n: number): number {
    return n <= 1 ? ASY1 : ASY0 + ((ASY1 - ASY0) * i) / (n - 1);
  }

  // ---- RESULT: dominant terminal ----------------------------------------
  const result = dto.result;
  const frozen = dto.frozenResult;
  const execution = dto.execution;

  return {
    question,
    problemAuthority: problem?.authority || 'PENDING',
    hasProblem: !!problem,

    discLed,
    discNodes,
    discLinks,
    discEvidenceCount: evidence.length,
    discFindingCount: findings.length,

    predCount: predictions.length,
    predAnyValue,
    predAllNotEval,
    predValues,

    recOption,
    humanSelected,
    humanDecisionId: human?.decisionId || null,
    humanAuthority: human?.authority || 'PENDING',
    humanPending,
    conflict: dto.projectionConflict,
    hasAlternatives: (dto.prescription?.alternatives?.length || 0) > 0,

    actionSteps,
    actionPresent: !!(ap && (ap.steps || []).length),
    actionStatus: ap?.status || '',
    actionTotal: (ap?.steps || []).length,

    resultId: result?.id || null,
    resultStatus: result?.status || '',
    resultSummary: truncate(result?.summary || '', 240),
    resultPresent: !!result,
    frozenId: frozen?.id || null,
    frozenStatus: frozen?.status || '',
    frozenSignature: (frozen?.signature || '').slice(0, 12),

    executionStatus: execution?.status || null,
    executionSimulated: !!execution?.simulated,
  };
}

export function CognitiveOperationMap({
  dto,
  graph,
  onSelectArtifact,
}: {
  dto: CognitiveProjectionDTO;
  graph: CognitiveProjectionGraph;
  onSelectArtifact?: (a: GraphArtifact) => void;
}) {
  const labelPolicy = useMemo(() => readLabelPolicy(), []);
  const hideLabels = labelPolicy === 'off';
  const bare = hideLabels && typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('bare') === '1';
  const m = useMemo(() => buildModel(dto, graph), [dto, graph]);

  const select = (id?: string | null) => {
    if (!id || !onSelectArtifact) return;
    const a = graph.nodes.find((n) => n.id === id);
    if (a) onSelectArtifact(a);
  };

  const dataReady = dto.problem || dto.evidence?.length || dto.findings?.length || dto.predictions?.length || dto.humanDecision?.selectedAlternativeId || dto.actionPlan || dto.result;

  return (
    <div
      className="opmap-root"
      data-op-map="1"
      data-cog-ready={hideLabels ? '1' : '0'}
      data-opmap-labels={labelPolicy}
      data-opmap-bare={bare ? '1' : '0'}
      data-opmap-stage={stageOf(m)}
      style={{ height: bare ? 'auto' : undefined }}
    >
      {!bare && (
        <div className="opmap-hud">
          <span className="opmap-hud-title">Cognitive Operation Map</span>
          <span className="opmap-hud-sub">CognitiveProjectionDTO · single source · 6 cognitive states</span>
          <span className="opmap-hud-hint">question → discovery → evaluation → decision → action → result</span>
        </div>
      )}

      <div className="opmap-canvas">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%" preserveAspectRatio="xMidYMid meet" role="img" aria-label={bare ? undefined : 'Cognitive operation map: question to result'}>
          <defs>
            <linearGradient id="opmap-terminal" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor={COL.result} stopOpacity="0.20" />
              <stop offset="1" stopColor={COL.result} stopOpacity="0.02" />
            </linearGradient>
            <linearGradient id="opmap-gate" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor={COL.authority} stopOpacity="0.12" />
              <stop offset="1" stopColor={COL.authority} stopOpacity="0.03" />
            </linearGradient>
          </defs>

          {/* ---------- SPINE (single cognitive axis) + directional flow ---------- */}
          <g className="opmap-geometry">
            <line x1={92} y1={SPINE_Y} x2={1125} y2={SPINE_Y} stroke={COL.hairline} strokeWidth={1.4} />
            <line x1={92} y1={SPINE_Y} x2={1125} y2={SPINE_Y} stroke={COL.grid} strokeWidth={0} />
            {[1125, 950, 760, 560, 330].map((x, i) => (
              <g key={i} transform={`translate(${x - 9},${SPINE_Y - 4})`}>
                <path d="M0,3 L8,3 L6,0 M8,3 L6,6" stroke={COL.textMicro} strokeWidth={1} fill="none" />
              </g>
            ))}
          </g>

          {/* ---------- QUESTION (ORIGIN · open ring) ---------- */}
          <g className="opmap-geometry">
            <circle cx={92} cy={SPINE_Y} r={17} fill="none" stroke={COL.problem} strokeWidth={2.2} />
            {/* hollow centre = empty opening */}
            <circle cx={92} cy={SPINE_Y} r={2.6} fill={COL.problem} />
          </g>
          <text x={92} y={SPINE_Y - 34} textAnchor="middle" className="opmap-label" fill={COL.problem} fontSize={11} fontWeight={700} fontFamily="var(--font-mono)" letterSpacing="0.08em">QUESTION</text>
          <text x={92} y={SPINE_Y + 36} textAnchor="middle" className="opmap-label opmap-sub" fill={COL.textLabel} fontSize={9} fontFamily="var(--font-mono)">{m.hasProblem ? truncate(m.question, 58) : 'NOT_AVAILABLE'}</text>

          {/* ---------- DISCOVERY (MANY → FEW convergence) ---------- */}
          <g className="opmap-geometry">
            {/* evidence source points (many) */}
            {m.discLed.map((d) => (
              <circle key={d.id} cx={d.x} cy={d.y} r={d.r} fill={COL.evidence} opacity={0.82} />
            ))}
            {/* real derived_from links */}
            {m.discLinks.map((l, i) => (
              <path key={i} d={`M ${l.fx} ${l.fy} C ${l.fx} ${(l.fy + l.ty) / 2} ${l.tx} ${(l.fy + l.ty) / 2} ${l.tx} ${l.ty}`} stroke={COL.textMicro} strokeWidth={0.9} fill="none" opacity={0.6} strokeDasharray={l.grounded ? '' : '2 3'} />
            ))}
            {/* distilled finding nodes (few) */}
            {m.discNodes.map((n) => (
              <g key={n.id} transform={`translate(${n.x},${n.y})`} onClick={() => select(n.id)} style={{ cursor: onSelectArtifact ? 'pointer' : 'default' }}>
                <rect x={-n.w / 2} y={-n.h / 2} width={n.w} height={n.h} rx={3} fill="#fff" stroke={statusColor(n.status)} strokeWidth={1.2} />
                <circle cx={-n.w / 2 + 8} cy={0} r={3.4} fill={statusColor(n.status)} />
                <text x={-n.w / 2 + 17} y={3.4} className="opmap-label" fontSize={8} fontFamily="var(--font-mono)" fill={COL.textLabel}>{truncate(n.id, 10)}</text>
              </g>
            ))}
          </g>
          <g className="opmap-label">
            <text x={182} y={160} fill={COL.evidence} fontSize={10.5} fontWeight={700} fontFamily="var(--font-mono)" letterSpacing="0.08em">DISCOVERY</text>
            <text x={182} y={176} fill={COL.textLabel} fontSize={8} fontFamily="var(--font-mono)">{m.discEvidenceCount} evidence → {m.discFindingCount} findings</text>
            {m.discFindingCount === 0 && <text x={310} y={330} textAnchor="middle" fill={COL.textMicro} fontSize={9} fontFamily="var(--font-mono)">DATA NOT AVAILABLE</text>}
          </g>

          {/* ---------- EVALUATION (measurement gauge) ---------- */}
          <g className="opmap-geometry">
            <line x1={478} y1={310} x2={618} y2={310} stroke={COL.hairline} strokeWidth={1.4} />
            {Array.from({ length: 13 }, (_, i) => i).map((i) => {
              const x = 478 + i * (140 / 12);
              return <line key={i} x1={x} y1={i % 3 === 0 ? 302 : 306} x2={x} y2={310} stroke={COL.textMicro} strokeWidth={i % 3 === 0 ? 1.1 : 0.7} />;
            })}
            {/* honest NOT_EVALUATED / value needle */}
            {m.predAllNotEval && (
              <g className="opmap-label">
                <rect x={478} y={318} width={140} height={22} fill={COL.amber} opacity={0.12} />
                <text x={548} y={333} textAnchor="middle" fill={COL.amber} fontSize={9} fontFamily="var(--font-mono)" fontWeight={700}>NOT_EVALUATED</text>
              </g>
            )}
            {!m.predAllNotEval && m.predAnyValue && (
              <g>
                {m.predValues.map((v, i) => {
                  const nx = 478 + Math.min(140, Math.max(0, (i / Math.max(1, m.predValues.length - 1)) * 140));
                  return <path key={i} d={`M ${nx - 6} 318 L ${nx} 302 L ${nx + 6} 318`} stroke={COL.prediction} strokeWidth={1.4} fill="none" />;
                })}
                <text x={548} y={348} textAnchor="middle" className="opmap-label" fill={COL.prediction} fontSize={8.5} fontFamily="var(--font-mono)">{m.predValues.join(', ')}</text>
              </g>
            )}
          </g>
          <g className="opmap-label">
            <text x={478} y={248} fill={COL.prediction} fontSize={10.5} fontWeight={700} fontFamily="var(--font-mono)" letterSpacing="0.07em">EVALUATION</text>
            <text x={478} y={264} fill={COL.textLabel} fontSize={7.6} fontFamily="var(--font-mono)">ACFL · MathEngine · GCLV · {m.predCount} pred</text>
            {m.predCount === 0 && <text x={548} y={340} textAnchor="middle" fill={COL.textMicro} fontSize={9} fontFamily="var(--font-mono)">DATA NOT AVAILABLE</text>}
          </g>

          {/* ---------- DECISION (sovereign authority gate) ---------- */}
          <g className="opmap-geometry">
            <rect x={644} y={186} width={168} height={248} rx={3} fill="url(#opmap-gate)" stroke={COL.authority} strokeWidth={1.6} />
            {/* the gate interrupts the horizontal rhythm -> a sovereign block */}
            <rect x={644} y={186} width={5} height={248} fill={COL.authority} opacity={0.85} />
          </g>
          <g className="opmap-label">
            <text x={728} y={210} textAnchor="middle" fill={COL.authority} fontSize={11} fontWeight={700} fontFamily="var(--font-mono)" letterSpacing="0.1em">HUMAN DECISION</text>
          </g>

          {/* RECOMMENDED track */}
          <g className="opmap-geometry">
            <g transform="translate(728,240)">
              <rect x={-68} y={-15} width={136} height={19} rx={2} fill="none" stroke={COL.rec} strokeWidth={1} opacity={0.8} />
              <circle cx={-58} cy={-5.5} r={2.6} fill={COL.rec} />
              <text x={-50} y={-1} className="opmap-label" fontSize={7.6} fontFamily="var(--font-mono)" fill={COL.rec} letterSpacing="0.06em">EUREKA RECOMMENDED</text>
            </g>
          </g>
          <g className="opmap-label">
            <rect x={752} y={231} width={72} height={16} rx={2} fill={COL.rec} opacity={0.08} />
            <text x={788} y={242} textAnchor="middle" fontSize={8.4} fontFamily="var(--font-mono)" fill={COL.rec} fontWeight={600}>{m.recOption ? truncate(m.recOption, 14) : '—'}</text>
          </g>

          {/* HUMAN DECIDED track (AuthorityChip visual language: violet dot + bordered mono label) */}
          <g className="opmap-geometry">
            <g transform="translate(728,300)">
              <rect x={-84} y={-24} width={168} height={34} rx={3} fill={COL.authority} opacity={0.16} stroke={COL.authority} strokeWidth={1.6} />
              <circle cx={-68} cy={-7} r={3} fill={COL.authority} />
              <text x={-58} y={-3.4} className="opmap-label" fontSize={7.8} fontFamily="var(--font-mono)" fill={COL.authority} letterSpacing="0.08em">HUMAN_AUTHORIZED</text>
              <text x={0} y={4.6} textAnchor="middle" className="opmap-label" fontSize={15} fontFamily="var(--font-mono)" fontWeight={700} fill={COL.authority}>{m.humanSelected ? m.humanSelected : '…'}</text>
            </g>
          </g>
          <g className="opmap-label">
            {m.humanPending ? (
              <text x={728} y={352} textAnchor="middle" fill={COL.textMicro} fontSize={8} fontFamily="var(--font-mono)">DECISION PENDING · human authority</text>
            ) : (
              <text x={728} y={352} textAnchor="middle" fill={COL.textLabel} fontSize={7.6} fontFamily="var(--font-mono)">{m.humanDecisionId ? truncate(m.humanDecisionId, 16) : ''}{m.conflict ? ' · conflict' : ''}</text>
            )}
            {m.conflict && (
              <g className="opmap-label">
                <rect x={652} y={406} width={152} height={0} fill="none" />
                <text x={728} y={420} textAnchor="middle" fill={COL.amber} fontSize={7.6} fontFamily="var(--font-mono)">projection conflict · action plan ≠ human decision</text>
              </g>
            )}
          </g>
          {!m.hasAlternatives && (
            <text x={728} y={416} textAnchor="middle" className="opmap-label" fill={COL.textMicro} fontSize={7.6} fontFamily="var(--font-mono)">no alternatives proposed</text>
          )}

          {/* ---------- ACTION (rising N-step staircase) ---------- */}
          <g className="opmap-geometry">
            {m.actionPresent ? (
              <>
                <path d={stairPath(m.actionSteps, 824, 1004, 432, 208)} stroke={COL.action} strokeWidth={1.5} fill="none" />
                {m.actionSteps.map((s) => (
                  <g key={s.order} transform={`translate(${s.x},${s.y})`}>
                    <circle r={9} fill="#fff" stroke={statusColor(s.status)} strokeWidth={1.6} />
                    <text y={3} textAnchor="middle" className="opmap-label" fontSize={7.4} fontFamily="var(--font-mono)" fontWeight={700} fill={statusColor(s.status)}>{String(s.order).padStart(2, '0')}</text>
                  </g>
                ))}
              </>
            ) : (
              <>
                <path d={`M 824 432 L 1004 208`} stroke={COL.textMicro} strokeWidth={1.2} fill="none" strokeDasharray="5 6" opacity={0.5} />
                <text x={914} y={330} textAnchor="middle" className="opmap-label" fill={COL.textMicro} fontSize={8} fontFamily="var(--font-mono)">DATA NOT AVAILABLE · no action plan</text>
              </>
            )}
          </g>
          <g className="opmap-label">
            <text x={824} y={170} fill={COL.action} fontSize={10.5} fontWeight={700} fontFamily="var(--font-mono)" letterSpacing="0.07em">ACTION</text>
            <text x={824} y={186} fill={COL.textLabel} fontSize={7.6} fontFamily="var(--font-mono)">{m.actionPresent ? `${m.actionTotal} steps · ${m.actionStatus}` : '0 steps'}</text>
            {m.actionPresent && m.actionTotal > m.actionSteps.length && (
              <text x={1004} y={196} textAnchor="end" fill={COL.textMicro} fontSize={7.2} fontFamily="var(--font-mono)">+{m.actionTotal - m.actionSteps.length} more</text>
            )}
          </g>

          {/* ---------- RESULT (dominant closed terminal) ---------- */}
          <g className="opmap-geometry">
            <rect x={1030} y={150} width={192} height={238} rx={4} fill="url(#opmap-terminal)" stroke={COL.result} strokeWidth={2.4} />
            {/* closure mark */}
            <rect x={1030} y={150} width={192} height={6} fill={COL.result} opacity={0.9} />
          </g>
          <g className="opmap-label">
            <text x={1126} y={186} textAnchor="middle" fill={COL.result} fontSize={12} fontWeight={700} fontFamily="var(--font-mono)" letterSpacing="0.12em">RESULT</text>
            <text x={1126} y={204} textAnchor="middle" fontSize={8} fontFamily="var(--font-mono)" fill={COL.textLabel}>
              {m.resultPresent ? m.resultStatus : 'DATA NOT AVAILABLE'}
            </text>
            <text x={1126} y={224} textAnchor="middle" fontSize={7.6} fontFamily="var(--font-mono)" fill={COL.textMicro}>
              {m.frozenSignature ? `FROZEN · ${m.frozenSignature}…` : m.executionSimulated ? 'SIMULATED' : ''}
            </text>
            <text x={1126} y={246} textAnchor="middle" fontSize={8} fontFamily="var(--font-sans)" fill={COL.textDisplay}>{truncate(m.resultSummary, 132)}</text>
            {m.resultId && <text x={1126} y={376} textAnchor="middle" fontSize={7.4} fontFamily="var(--font-mono)" fill={COL.textMicro}>{m.resultId}</text>}
          </g>
        </svg>
      </div>

      {!bare && (
        <div className="opmap-sr" aria-live="polite">
          <strong>Cognitive operation:</strong> {m.question ? truncate(m.question, 90) : 'no question'} · {m.discFindingCount} findings · {m.predCount} predictions · {m.humanPending ? 'human decision pending' : `human decided ${m.humanSelected}`} · {m.actionPresent ? `${m.actionTotal} actions` : 'no action plan'} · {m.resultPresent ? m.resultStatus : 'DATA NOT AVAILABLE'}
        </div>
      )}
    </div>
  );
}

function stairPath(steps: StepNode[], x0: number, x1: number, y0: number, y1: number): string {
  if (!steps.length) return '';
  if (steps.length === 1) return `M ${x0} ${y0} L ${x1} ${y1}`;
  let d = `M ${x0} ${y0}`;
  steps.forEach((s, i) => {
    const px = i === 0 ? x0 : steps[i - 1].x;
    const py = i === 0 ? y0 : steps[i - 1].y;
    d += ` L ${s.x} ${py} L ${s.x} ${s.y}`;
  });
  return d;
}

// Stage descriptor used only for the data-opmap-stage instrumentation.
function stageOf(m: MapModel): string {
  return [m.hasProblem ? 'question' : '', m.discFindingCount ? 'discovery' : '', m.predCount ? 'evaluation' : '', m.humanPending ? 'decision-pending' : 'decision', m.actionPresent ? 'action' : '', m.resultPresent ? 'result' : ''].filter(Boolean).join('|');
}

export default CognitiveOperationMap;
