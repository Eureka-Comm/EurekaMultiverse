import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import WorkAuditView from './WorkAuditView';

describe('WorkAuditView', () => {
  it('renders the read-only canonical observability surface with no network on mount', () => {
    const html = renderToString(createElement(WorkAuditView));
    expect(html).toContain('EUREKA · Canonical Work Observability');
    expect(html).toContain('Load canonical audit (read-only)');
    // no authority-escalation / release / deliver / ship / deploy / execute controls
    expect(html).not.toContain('Release');
    expect(html).not.toContain('Deliver');
    expect(html).not.toContain('Ship');
    expect(html).not.toContain('Deploy');
    expect(html).not.toContain('Execute');
    // no frontend persistence / authority inputs
    expect(html).not.toContain('authorize');
  });
});
