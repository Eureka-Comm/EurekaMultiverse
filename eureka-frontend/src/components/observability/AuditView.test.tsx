import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import AuditView from './AuditView';

describe('AuditView', () => {
  it('renders the read-only observability surface with no network on mount', () => {
    const html = renderToString(createElement(AuditView));
    expect(html).toContain('EUREKA · Observability / Audit');
    expect(html).toContain('Load audit (read-only)');
    // no authority-escalation / execution / recommendation / winner controls
    expect(html).not.toContain('Promote');
    expect(html).not.toContain('Execute');
    expect(html).not.toContain('Recommendation');
    expect(html).not.toContain('Winner');
    // the view only inspects; it does not expose an POST/authorize action
    expect(html).not.toContain('authorize');
  });
});
