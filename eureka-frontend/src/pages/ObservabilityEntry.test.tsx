import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import ObservabilityEntry from './ObservabilityEntry';

describe('ObservabilityEntry', () => {
  it('renders the productive CONSTELACIÓN entry with the shell and observatory, no domain mixing', () => {
    const html = renderToString(createElement(ObservabilityEntry));
    // productive shell present (sidebar nav) + the CONSTELACIÓN observatory
    expect(html).toContain('Observability');
    expect(html).toContain('EUREKA · CONSTELACIÓN · Observatorio Cognitivo');
    // observatories still distinct
    expect(html).toContain('CANONICAL');
    expect(html).toContain('COGNITIVE');
    expect(html).toContain('HYPOTHETICAL');
    expect(html).toContain('EVIDENCE');
    expect(html).toContain('GOVERNANCE');
    // read-only, no authority-escalation / release / deliver / ship / deploy / execute controls
    expect(html).not.toContain('Release');
    expect(html).not.toContain('Deliver');
    expect(html).not.toContain('Ship');
    expect(html).not.toContain('Deploy');
    expect(html).not.toContain('Execute');
    // no frontend persistence in the entry
    expect(html).not.toContain('localStorage');
    expect(html).not.toContain('sessionStorage');
    expect(html).not.toContain('IndexedDB');
  });
});
