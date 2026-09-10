import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import GovernanceMap from './GovernanceMap';
import CognitiveObservatory from './CognitiveObservatory';

describe('GovernanceMap', () => {
  it('renders the authority map (LLM proposes, EUREKA governs, ACFL/Human/Q4/Publisher) with no release/execution', () => {
    const html = renderToString(createElement(GovernanceMap));
    expect(html).toContain('Governance Observatory · Authority Map');
    expect(html).toContain('DeepSeek / Ollama');
    expect(html).toContain('PROPOSE');
    expect(html).toContain('EUREKA');
    expect(html).toContain('ACFL');
    expect(html).toContain('Human');
    expect(html).toContain('Q4 EffectBoundary');
    expect(html).toContain('EM Publisher');
    // no release / execution / authority claims from the map
    expect(html).not.toContain('Release');
    expect(html).not.toContain('Execute');
    expect(html).not.toContain('Deliver');
    expect(html).not.toContain('Ship');
  });
});

describe('CognitiveObservatory', () => {
  it('renders the read-only cognitive observatory surface with no fetch on mount', () => {
    // renderToString won't run effects -> no network on mount; initial render is the empty/loading state
    const html = renderToString(createElement(CognitiveObservatory, { workId: 'WORK-AC8CD7B1' }));
    expect(html).toContain('Cognitive Observatory · Cognitive Pipeline');
    expect(html).toContain('Contractual pipeline');
    expect(html).toContain('Observed pipeline');
    // no release / execution / authority-escalation controls
    expect(html).not.toContain('Release');
    expect(html).not.toContain('Execute');
    expect(html).not.toContain('Deliver');
    expect(html).not.toContain('Ship');
  });

  it('renders a fail-closed "enter a Work id" prompt (no network) when the id is empty', () => {
    const html = renderToString(createElement(CognitiveObservatory, { workId: '' }));
    expect(html).toContain('Enter a Work id to observe the cognitive trace');
    // never fabricates trace content for an absent work
    expect(html).not.toContain('No cognitive invocation recorded');
  });
});
