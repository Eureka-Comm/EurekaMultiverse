import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import WhatIfView from './WhatIfView';

describe('WhatIfView', () => {
  it('renders the hypothetical-scenario surface with no network on mount', () => {
    const html = renderToString(createElement(WhatIfView));
    expect(html).toContain('What-If · Hypothetical Scenario');
    expect(html).toContain('Run WHAT-IF');
    expect(html).toContain('Delta');
    expect(html).toContain('Compare');
    // no authority-escalation / execution controls
    expect(html).not.toContain('Promote');
    expect(html).not.toContain('Execute');
    expect(html).not.toContain('Recommendation');
    expect(html).not.toContain('Winner');
  });
});
