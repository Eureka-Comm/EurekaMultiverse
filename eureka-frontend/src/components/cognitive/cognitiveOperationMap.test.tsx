import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import { buildCognitiveProjection } from '../../domain/cognitiveProjection';
import { buildCognitiveProjectionGraph } from '../../domain/cognitiveProjectionGraph';
import { CognitiveOperationMap } from './CognitiveOperationMap';

const completedPath = fileURLToPath(new URL('../../fixtures/eureka_completed_state.json', import.meta.url));
const conflictPath = fileURLToPath(new URL('../../fixtures/eureka_conflict_state.json', import.meta.url));
const openPath = fileURLToPath(new URL('../../../public/__shot_state.json', import.meta.url));

const completed = JSON.parse(readFileSync(completedPath, 'utf8'));
const conflict = JSON.parse(readFileSync(conflictPath, 'utf8'));
const open = JSON.parse(readFileSync(openPath, 'utf8'));

describe('COGNITIVE OPERATION MAP (LS94) — single-surface comprehension + honesty', () => {
  it('renders all 6 stage primitives over a real completed DTO (no card wall: distinct forms)', () => {
    const dto = buildCognitiveProjection(completed);
    const graph = buildCognitiveProjectionGraph(dto);
    const html = renderToString(createElement(CognitiveOperationMap, { dto, graph }));
    expect(html).toContain('QUESTION');
    expect(html).toContain('DISCOVERY');
    expect(html).toContain('EVALUATION');
    expect(html).toContain('HUMAN DECISION');
    expect(html).toContain('ACTION');
    expect(html).toContain('RESULT');
  });

  it('surfaces the PERSON HUMAN AUTHORITY and keeps the recommendation distinct', () => {
    const dto = buildCognitiveProjection(completed);
    const graph = buildCognitiveProjectionGraph(dto);
    const html = renderToString(createElement(CognitiveOperationMap, { dto, graph }));
    // Human decision is ALT-001 with the AuthorityChip visual language (violet label).
    expect(html).toContain('HUMAN_AUTHORIZED');
    expect(html).toContain('ALT-001');
    // A distinct EUREKA RECOMMENDED track is rendered even when null.
    expect(html).toContain('EUREKA RECOMMENDED');
  });

  it('honestly marks the completed state (NOT_EVALUATED gauge, DATA NOT AVAILABLE action, FROZEN result)', () => {
    const dto = buildCognitiveProjection(completed);
    const graph = buildCognitiveProjectionGraph(dto);
    const html = renderToString(createElement(CognitiveOperationMap, { dto, graph }));
    expect(html).toContain('NOT_EVALUATED');                 // predictions all not evaluated
    expect(html).toContain('DATA NOT AVAILABLE');            // no action plan => absent stage shown honestly
    expect(html).toContain('FROZEN');                        // frozen result
    expect(html).toContain('ACFL');                          // evaluation engine identity, never fabricated
  });

  it('derived state: recommendation != human decision is surfaced as two distinct tracks + conflict', () => {
    const dto = buildCognitiveProjection(conflict);
    expect(dto.recommendedOption).toBe('ALT-002');
    expect(dto.humanDecision.selectedAlternativeId).toBe('ALT-001');
    expect(dto.projectionConflict).toBe(true);
    expect(dto.actionPlan?.steps?.length).toBe(4);
    const graph = buildCognitiveProjectionGraph(dto);
    const html = renderToString(createElement(CognitiveOperationMap, { dto, graph }));
    expect(html).toContain('EUREKA RECOMMENDED');
    expect(html).toContain('ALT-002');                       // system recommendation (candidate)
    expect(html).toContain('ALT-001');                       // human decision
    expect(html).toContain('projection conflict');           // never auto-corrected
    expect(html).toContain('4 steps');                       // exact real N steps, not invented
  });

  it('open-research state renders honest markers (no decision yet, no action plan, no predictions)', () => {
    const dto = buildCognitiveProjection(open);
    const graph = buildCognitiveProjectionGraph(dto);
    const html = renderToString(createElement(CognitiveOperationMap, { dto, graph }));
    expect(html).toContain('DECISION PENDING');
    expect(html).toContain('DATA NOT AVAILABLE');            // action plan absent
    expect(html).not.toContain('projection conflict');
  });

  it('carries the comprehension-surface instrumentation attributes', () => {
    const dto = buildCognitiveProjection(completed);
    const graph = buildCognitiveProjectionGraph(dto);
    const html = renderToString(createElement(CognitiveOperationMap, { dto, graph }));
    expect(html).toContain('data-op-map="1"');
    expect(html).toContain('data-opmap-labels="on"');
    expect(html).toContain('data-cog-ready="0"');            // labels are shown in SSR (no window)
  });
});
