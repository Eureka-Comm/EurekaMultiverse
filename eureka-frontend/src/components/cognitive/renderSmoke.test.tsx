import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import { buildCognitiveProjection } from '../../domain/cognitiveProjection';
import { buildCognitiveProjectionGraph } from '../../domain/cognitiveProjectionGraph';
import { AuthorityChip } from './AuthorityChip';
import { DecisionView } from './DecisionView';
import { StorytellingPanel } from './StorytellingPanel';
import { ProvenanceChain } from './ProvenanceChain';
import { Inspector } from './Inspector';
import { OpenChapter } from './chapters/OpenChapter';
import { ExecutiveCognitiveAnswer } from './ExecutiveCognitiveAnswer';

const fixturePath = fileURLToPath(new URL('../../fixtures/eureka_completed_state.json', import.meta.url));

// A minimal valid canonical state carrying the governed `open_research` projection.
function openBase(): any {
  return {
    schema_version: 'EUREKA_CANONICAL_WORK_STATE_V2',
    work: { workId: 'W-OPEN', status: 'RUNNING', userIntent: 'Estado de la evidencia sobre X' },
    execution_plan: { steps: [] },
    state: {},
    evidence: [],
    extracted_evidence: {},
    visualizations: [],
    available_capabilities: [],
    gaps: [],
    conditions: [],
    revision: 1,
    extracted_entities: {},
    open_research: {
      status: 'OPEN_INSUFFICIENT_INFORMATION',
      operation_kind: 'OPEN_RESEARCH',
      is_open: true,
      decision_reached: false,
      decision_pending: true,
      items: [
        { kind: 'UNRESOLVED_QUESTION', label: 'No hay datos sobre X', source_ref: 'knowledge.unknowns[0]' },
        { kind: 'PENDING_HUMAN_DECISION', label: 'No human decision yet', source_ref: 'human_decision' },
      ],
      decision_relevant_knowledge: ['FND-1'],
      summary: 'Operation is open - no human decision has been reached.',
    },
  };
}

/**
 * §28 E2E (render layer) — presentational components mount over the REAL DTO
 * without throwing and surface the correct authority / decision semantics. Uses
 * react-dom/server renderToString (node env) since Playwright is not installed.
 */
describe('COGNITIVE STORY render smoke (real DTO)', () => {
  it('authority chips render the correct text labels (color + label, never color-only)', () => {
    const html = renderToString(createElement(AuthorityChip, { authority: 'NOT_EVALUATED' }));
    expect(html).toContain('NOT_EVALUATED');
    const sim = renderToString(createElement(AuthorityChip, { authority: 'SIMULATED' }));
    expect(sim).toContain('SIMULATED');
    const hum = renderToString(createElement(AuthorityChip, { authority: 'HUMAN_AUTHORIZED' }));
    expect(hum).toContain('HUMAN_AUTHORIZED');
  });

  it('DecisionView shows HUMAN DECISION = human_decision and never the recommendation', () => {
    const state = JSON.parse(readFileSync(fixturePath, 'utf8'));
    const dto = buildCognitiveProjection(state);
    const html = renderToString(createElement(DecisionView, { dto }));
    // The human selection is ALT-001 (human_decision), authority HUMAN_AUTHORIZED.
    expect(html).toContain('ALT-001');
    expect(html).toContain('HUMAN_AUTHORIZED');
    expect(html).toContain('HUMAN DECISION');
    expect(html).toContain('ALTERNATIVES');
  });

  it('StorytellingPanel renders the real question + decision without throwing', () => {
    const state = JSON.parse(readFileSync(fixturePath, 'utf8'));
    const dto = buildCognitiveProjection(state);
    const html = renderToString(createElement(StorytellingPanel, { dto }));
    expect(html).toContain('Executive summary');
    expect(html).toContain('What the human decided');
    expect(html).toContain('HUMAN_AUTHORIZED');
    expect(html).toBeTruthy();
  });

  it('ProvenanceChain renders the real DECISION id and the honest DATA NOT AVAILABLE steps', () => {
    const state = JSON.parse(readFileSync(fixturePath, 'utf8'));
    const dto = buildCognitiveProjection(state);
    const html = renderToString(createElement(ProvenanceChain, { dto }));
    expect(html).toContain('DEC-8b8482');
    expect(html).toContain('DATA NOT AVAILABLE'); // action/execution absent -> honest
  });

  it('Inspector surfaces the DECISION artifact authority + provenance', () => {
    const state = JSON.parse(readFileSync(fixturePath, 'utf8'));
    const dto = buildCognitiveProjection(state);
    const graph = buildCognitiveProjectionGraph(dto);
    const dec = graph.nodes.find((n) => n.kind === 'DECISION')!;
    const html = renderToString(createElement(Inspector, { artifacts: [dec] }));
    expect(html).toContain('DEC-8b8482');
    expect(html).toContain('HUMAN_AUTHORIZED');
    expect(html).toContain('EM Prescriptor / EM Installer');
  });

  // ---- LS90 — OPEN cognitive operation (what remains open) ----
  it('OpenChapter renders the OPEN leading edge honestly (open research, no decision)', () => {
    const state = openBase();
    const dto = buildCognitiveProjection(state as any);
    const graph = buildCognitiveProjectionGraph(dto);
    const html = renderToString(createElement(OpenChapter, {
      dto,
      graph,
      onSelectArtifact: () => {},
      workId: 'W-OPEN',
      workStatus: 'RUNNING',
    }));
    expect(html).toContain('What remains open');
    expect(html).toContain('OPEN');
    expect(html).toContain('OPEN_RESEARCH');
    expect(html).toContain('decision still pending');
    expect(html).toContain('UNRESOLVED_QUESTION');
    expect(html).toContain('PENDING_HUMAN_DECISION');
    expect(html).toContain('No hay datos sobre X');
    // Never presented as a closed decision
    expect(html).not.toContain('HUMAN_AUTHORIZED');
  });

  it('ExecutiveCognitiveAnswer shows WHAT REMAINS OPEN and never a closed decision for an open work', () => {
    const state = openBase();
    const dto = buildCognitiveProjection(state as any);
    const html = renderToString(createElement(ExecutiveCognitiveAnswer, { dto, onExplore: () => {} }));
    expect(html).toContain('WHAT REMAINS OPEN');
    expect(html).toContain('OPEN RESEARCH OPERATION');
    expect(html).toContain('no decision yet');
    expect(html).toContain('PENDING_HUMAN_DECISION');
  });
});
