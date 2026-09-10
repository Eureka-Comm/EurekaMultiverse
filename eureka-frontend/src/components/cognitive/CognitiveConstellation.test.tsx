import { describe, it, expect, afterEach } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import CognitiveConstellation from './CognitiveConstellation';
import { useWorkStore } from '../../store/workStore';

afterEach(() => useWorkStore.setState({ activeWork: null, appState: 'NO_WORK' }));

describe('CognitiveConstellation — honest empty state (adversarial, fail-closed)', () => {
  it('renders a truthful empty state when there is no active work — never a fabricated graph', () => {
    useWorkStore.setState({ activeWork: null, appState: 'NO_WORK' });
    const html = renderToString(createElement(CognitiveConstellation));
    expect(html).toContain('No active work');
    expect(html).toContain('Load Work');
    // a no-work surface must NOT draw a graph or a control deck / metrics
    expect(html).not.toContain('Graph Summary');
    expect(html).not.toContain('Focus Filter');
    expect(html).not.toContain('OBJECTS');
    expect(html).not.toContain('EUREKA COGNITIVE CORE');
  });
});
