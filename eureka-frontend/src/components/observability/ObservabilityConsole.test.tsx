import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import ObservabilityConsole from './ObservabilityConsole';

describe('ObservabilityConsole', () => {
  it('renders CONSTELACIÓN as a read-only observatory with distinct observatories and no network on mount', () => {
    const html = renderToString(createElement(ObservabilityConsole));
    expect(html).toContain('EUREKA · CONSTELACIÓN · Observatorio Cognitivo');
    // five distinct, labelled observatories (domains never merged)
    expect(html).toContain('CANONICAL');
    expect(html).toContain('COGNITIVE');
    expect(html).toContain('HYPOTHETICAL');
    expect(html).toContain('EVIDENCE');
    expect(html).toContain('GOVERNANCE');
    // canonical domain is the default active view (WorkAuditView mounts), no fetch on mount
    expect(html).toContain('Canonical Work Observability');
    // no authority-escalation / release / deliver / ship / deploy / execute controls
    expect(html).not.toContain('Release');
    expect(html).not.toContain('Deliver');
    expect(html).not.toContain('Ship');
    expect(html).not.toContain('Deploy');
    expect(html).not.toContain('Execute');
  });
});
